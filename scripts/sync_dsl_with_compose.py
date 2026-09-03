#!/usr/bin/env python3
"""
Сравнивает сервисы из docker-compose.yml с контейнерами в workspace.dsl.
Если найден сервис, которого нет в модели, — добавляет заготовку блока
container с пометкой TODO, чтобы связи (Rel) дозаполнил человек вручную.

Скрипт НЕ пытается угадывать смысловые связи между контейнерами —
это осознанное архитектурное решение, а не то, что можно надёжно
вывести из docker-compose.yml.
"""

import re
import sys

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
        stub_lines.append(
            f'            {svc} = container "{svc}" "TODO: описать назначение" '
            f'"TODO: технология"  // auto-added, требует ручного заполнения связей'
        )

    lines[insert_idx:insert_idx] = stub_lines
    return "\n".join(lines)


def main():
    compose_services = get_compose_services()
    dsl_containers, content = get_dsl_containers()

    missing_in_dsl = compose_services - dsl_containers
    missing_in_compose = dsl_containers - compose_services

    if missing_in_compose:
        print(f"::warning::В workspace.dsl есть контейнеры, которых больше нет в compose: {missing_in_compose}")
        print("Это не критично, но стоит вручную удалить устаревшие блоки из workspace.dsl")

    if missing_in_dsl:
        print(f"::warning::Обнаружены новые сервисы без модели: {missing_in_dsl}")
        new_content = add_stub_containers(content, missing_in_dsl)
        with open(DSL_FILE, "w") as f:
            f.write(new_content)
        print(f"Добавлены заготовки для: {missing_in_dsl}. Требуется ручное дополнение связей (Rel).")
    else:
        print("Drift не обнаружен, все сервисы уже есть в модели.")


if __name__ == "__main__":
    main()
