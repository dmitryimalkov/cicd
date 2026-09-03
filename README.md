# Test Stand — CI/CD + автоматизация архитектуры

## Что мы строим

Этот репозиторий — минимальный тестовый стенд для отработки двух связанных
автоматизаций:

1. **Автодеплой по push.** При изменении `docker-compose.yml` в ветке `main`
   GitHub Actions по SSH заходит на сервер, забирает изменения и
   перезапускает контейнеры (`docker compose up -d`).

2. **Автосинхронизация архитектурной модели.** При изменении
   `docker-compose.yml` или `workspace.dsl` отдельный job:
   - сравнивает список сервисов из `docker-compose.yml` со списком
     контейнеров в `workspace.dsl` (C4-модель в формате Structurizr DSL);
   - если появился новый сервис, которого нет в модели — добавляет для
     него заготовку блока `container` с пометкой `TODO` (связи между
     контейнерами скрипт не угадывает, это остаётся за человеком);
   - рендерит `workspace.dsl` в PlantUML, а затем в PNG-диаграммы
     (`SystemContext.png`, `Containers.png`);
   - коммитит обновлённые `workspace.dsl` и диаграммы обратно в
     репозиторий.

Оба job'а запускаются от одного и того же push и работают независимо друг
от друга. Оба используют прямой `git push` в `main` — предполагается, что
branch protection на ветке `main` не включена (если включите позже,
job с архитектурой нужно будет переделать под создание Pull Request).

## Структура репозитория

```
test-stand/
├── docker-compose.yml          # тестовый стек: nginx, app, postgres, redis
├── workspace.dsl               # C4-модель (Structurizr DSL)
├── architecture/
│   └── diagrams/                # сюда рендерятся .puml и .png
├── scripts/
│   ├── sync_dsl_with_compose.py # drift-check + автодополнение workspace.dsl
│   └── render_architecture.sh   # рендер workspace.dsl → PlantUML → PNG
└── .github/workflows/
    └── pipeline.yml              # deploy + architecture-sync
```

## Как настроить secrets в GitHub

Секреты нужны только для job `deploy` — он подключается к серверу по SSH.
Job `architecture-sync` секретов не требует (работает полностью на
GitHub-раннере, коммитит через встроенный `GITHUB_TOKEN`, который GitHub
подставляет автоматически).

1. Создайте отдельную SSH-пару **только для CI**, не используйте свой
   личный ключ:
   ```bash
   ssh-keygen -t ed25519 -f ./deploy_key -N "" -C "github-actions-deploy"
   ```
   Это создаст `deploy_key` (приватный) и `deploy_key.pub` (публичный).

2. Публичный ключ добавьте на сервер в `~/.ssh/authorized_keys` того
   пользователя, под которым будет выполняться деплой:
   ```bash
   ssh-copy-id -i deploy_key.pub deploy-user@ВАШ_СЕРВЕР
   ```
   (или вручную допишите содержимое `deploy_key.pub` в
   `/home/deploy-user/.ssh/authorized_keys` на сервере).

3. В репозитории на GitHub откройте
   **Settings → Secrets and variables → Actions → New repository secret**
   и добавьте четыре секрета:

   | Имя секрета | Значение |
   |---|---|
   | `SSH_HOST` | IP-адрес или домен вашей ВМ на cloud.ru |
   | `SSH_USER` | имя пользователя для деплоя (не root) |
   | `SSH_KEY` | содержимое приватного ключа `deploy_key` целиком, включая строки `-----BEGIN...` / `-----END...` |
   | `SSH_PORT` | порт SSH (обычно `22`, если не меняли) |

4. Удалите локальные файлы `deploy_key` / `deploy_key.pub` после того,
   как приватный ключ сохранён в GitHub Secrets — держать его на диске
   без необходимости не стоит.

5. Проверить, что секреты подставляются корректно, можно только через
   реальный запуск workflow (GitHub никогда не показывает значения
   секретов в логах, даже вам). Если `deploy` job падает на шаге
   `Deploy via SSH` с `Permission denied (publickey)` — почти всегда
   это означает, что публичный ключ не добавлен на сервере либо
   `SSH_USER`/`SSH_HOST` указаны неверно.

## Как проверить, что structurizr-cli корректно экспортирует workspace.dsl

Перед тем как полагаться на CI, стоит прогнать те же шаги локально —
на своей машине или прямо на тестовой ВМ на cloud.ru (потребуется только
Docker, ничего больше устанавливать не нужно).

1. **Проверить синтаксис DSL** (быстрая проверка без рендера):
   ```bash
   docker run --rm \
     -v "$(pwd):/usr/local/structurizr" \
     structurizr/cli validate -workspace workspace.dsl
   ```
   Если DSL некорректен, `structurizr-cli` выведет конкретную строку
   и описание ошибки (например, незакрытую скобку или ссылку на
   несуществующий элемент в `Rel`).

2. **Экспортировать в PlantUML и посмотреть на сырой вывод:**
   ```bash
   mkdir -p architecture/diagrams
   docker run --rm \
     -v "$(pwd):/usr/local/structurizr" \
     structurizr/cli export -workspace workspace.dsl -format plantuml -output architecture/diagrams

   cat architecture/diagrams/*.puml
   ```
   Если экспорт прошёл успешно — в папке появятся файлы `SystemContext.puml`
   и `Containers.puml` с текстовым описанием диаграмм на языке PlantUML.
   Если в выводе пусто или файлов нет — проверьте, что в `workspace.dsl`
   действительно есть блок `views` с `systemContext` и `container` view
   (без них экспортировать нечего).

3. **Отрендерить PlantUML в PNG и открыть глазами:**
   ```bash
   docker run --rm \
     -v "$(pwd)/architecture/diagrams:/data" \
     plantuml/plantuml -tpng "/data/*.puml"
   ```
   Откройте `architecture/diagrams/Containers.png` — на схеме должны быть
   все контейнеры из `workspace.dsl` со стрелками связей и подписями
   (не просто "depends on", а те смысловые описания, что вы указали в
   `Rel(...)`).

4. **Прогнать весь пайплайн одной командой** (то же самое, что выполнит
   CI):
   ```bash
   bash scripts/render_architecture.sh
   ```

5. **Проверить drift-check отдельно**, не трогая рендер — полезно, если
   просто хочется убедиться, что все сервисы из `docker-compose.yml`
   учтены в модели:
   ```bash
   pip install pyyaml
   python scripts/sync_dsl_with_compose.py
   ```
   Скрипт выведет `::warning::`, если найдёт сервис без модели, и сам
   допишет для него заготовку в `workspace.dsl` — после этого стоит
   открыть файл и убедиться, что заготовка добавилась в нужное место
   (внутри блока `softwareSystem { ... }`), а не за его пределами.

6. **Частая проблема на этапе тестирования на cloud.ru** — недоступность
   Docker Hub из региона или медленная скачка образов `structurizr/cli` и
   `plantuml/plantuml`. Проверьте это отдельно до встраивания в CI:
   ```bash
   docker pull structurizr/cli
   docker pull plantuml/plantuml
   ```
   Если `pull` зависает или падает — рендер лучше оставить только на
   стороне GitHub-раннера (`ubuntu-latest`), у которого с Docker Hub
   проблем нет, а на ВМ Docker вообще не использовать для этой задачи —
   готовые PNG туда попадут через `git pull`, как обычные файлы.
