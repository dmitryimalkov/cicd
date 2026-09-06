#!/usr/bin/env python3
"""
Сравнивает сервисы из docker-compose.yml с контейнерами в workspace.dsl
и полностью синхронизирует модель в обе стороны:
- сервис появился в compose, но его нет в модели -> добавляет заготовку
  container с пометкой TODO (связи дозаполняет человек вручную);
- сервис пропал из compose, но остался в модели -> удаляет объявление
  container и ВСЕ связи (Rel), где этот контейнер участвует как
  источник или назначение.

Внимание: автоматическое удаление стирает и связи, которые были
дописаны вручную для этого контейнера. Если контейнер временно убрали
из compose, но хотят сохранить его описание в архитектуре — нужно
не удалять сервис из compose, а закомментировать его иначе, либо
восстановить блок в workspace.dsl вручную после отката.
"""

import re

import yaml

COMPOSE_FILE = "docker-compose.yml"
DSL_FILE = "workspace.dsl"


def get_compose_services():
    with open(COMPOSE_FILE) as f:
        data = yaml.safe_load(f)
    return set(data.get("services", {}).keys())


def get_dsl_containers():
    with open(DSL_FILE) as f:
        content = f.read()
    matches = re.findall(r'(\w+)\s*=\s*container\s+"([^"]+)"', content)
    return {name for name, _ in matches}, content


def add_stub_containers(content, missing_services):
    lines = content.split("\n")
    insert_idx = None

    for i, line in enumerate(lines):
        if re.match(r"\s*softwareSystem\s*=\s*softwareSystem", line):
            depth = 0
            for j in range(i, len(lines)):
                depth += lines[j].count("{") - lines[j].count("}")
                if depth == 0 and j > i:
                    insert_idx = j
                    break
            break

    if insert_idx is None:
        print("::warning::Не удалось найти softwareSystem блок для вставки, добавьте вручную")
        return content

    stub_lines = []
    for svc in sorted(missing_services):
        stub_lines.append("            // auto-added, требует ручного заполнения связей (Rel)")
        stub_lines.append(
            f'            {svc} = container "{svc}" "TODO: описать назначение" "TODO: технология"'
        )

    lines[insert_idx:insert_idx] = stub_lines
    return "\n".join(lines)


def remove_stale_containers(content, stale_services):
    lines = content.split("\n")
    result = []
    skip_next_comment_for = None

    for line in lines:
        stripped = line.strip()

        # Пропускаем строку объявления удалённого контейнера
        matched_container = None
        for svc in stale_services:
            if re.match(rf'^{re.escape(svc)}\s*=\s*container\b', stripped):
                matched_container = svc
                break
        if matched_container:
            continue

        # Пропускаем автогенерированный комментарий-пометку прямо перед
        # строкой container (если следующая строка была бы объявлением
        # удалённого контейнера) — определяем "заглядыванием" не нужен,
        # проще: комментарий auto-added, если следующая содержательная
        # строка относится к удаляемому контейнеру, тоже отфильтруем ниже
        # отдельным проходом.

        # Пропускаем строки связей (Rel), где контейнер — источник или назначение
        is_stale_rel = False
        for svc in stale_services:
            if re.match(rf'^{re.escape(svc)}\s*->', stripped) or re.search(rf'->\s*{re.escape(svc)}\b', stripped):
                is_stale_rel = True
                break
        if is_stale_rel:
            continue

        result.append(line)

    # Второй проход: убираем осиротевшие "// auto-added..." комментарии,
    # за которыми теперь ничего не следует из того же блока (эвристика:
    # комментарий auto-added, за которым сразу идёт другой комментарий
    # auto-added или закрывающая скобка/пустая строка, а не container).
    cleaned = []
    for i, line in enumerate(result):
        if "// auto-added" in line:
            next_line = result[i + 1].strip() if i + 1 < len(result) else ""
            if not re.match(r'\w+\s*=\s*container\b', next_line):
                continue
        cleaned.append(line)

    return "\n".join(cleaned)


def main():
    compose_services = get_compose_services()
    dsl_containers, content = get_dsl_containers()

    missing_in_dsl = compose_services - dsl_containers
    missing_in_compose = dsl_containers - compose_services

    changed = False

    if missing_in_compose:
        print(f"::warning::Сервисы удалены из compose, чистим модель: {missing_in_compose}")
        content = remove_stale_containers(content, missing_in_compose)
        changed = True

    if missing_in_dsl:
        print(f"::warning::Обнаружены новые сервисы без модели: {missing_in_dsl}")
        content = add_stub_containers(content, missing_in_dsl)
        changed = True

    if changed:
        with open(DSL_FILE, "w") as f:
            f.write(content)
        print("workspace.dsl синхронизирован с docker-compose.yml.")
        if missing_in_dsl:
            print(f"Добавлены заготовки для: {missing_in_dsl}. Требуется ручное дополнение связей (Rel).")
    else:
        print("Drift не обнаружен, модель уже соответствует compose.")


if __name__ == "__main__":
    main()
