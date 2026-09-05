#!/usr/bin/env bash
set -e

WORKSPACE_FILE="workspace.dsl"
OUTPUT_DIR="architecture/diagrams"
STRUCTURIZR_CLI_VERSION="2024.12.07"

mkdir -p "$OUTPUT_DIR"

echo "==> Валидация DSL"
docker run --rm \
  -v "$(pwd):/usr/local/structurizr" \
  structurizr/cli:$STRUCTURIZR_CLI_VERSION validate -workspace "$WORKSPACE_FILE"

echo "==> Экспорт в PlantUML"
docker run --rm \
  -v "$(pwd):/usr/local/structurizr" \
  structurizr/cli:$STRUCTURIZR_CLI_VERSION export -workspace "$WORKSPACE_FILE" -format plantuml -output "$OUTPUT_DIR"

echo "==> Содержимое $OUTPUT_DIR после экспорта:"
ls -la "$OUTPUT_DIR"

shopt -s nullglob
PUML_FILES=("$OUTPUT_DIR"/*.puml)
shopt -u nullglob

if [ ${#PUML_FILES[@]} -eq 0 ]; then
  echo "::error::Экспорт не создал ни одного .puml файла. Проверьте workspace.dsl (блок views) и вывод шага export выше."
  exit 1
fi

echo "==> Рендер PlantUML в PNG"
for f in "${PUML_FILES[@]}"; do
  fname=$(basename "$f")
  docker run --rm \
    --user "$(id -u):$(id -g)" \
    -v "$(pwd)/$OUTPUT_DIR:/data" \
    plantuml/plantuml -tpng "/data/$fname"
done

echo "==> Готово. Файлы в $OUTPUT_DIR"
ls -la "$OUTPUT_DIR"
