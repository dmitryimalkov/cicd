#!/usr/bin/env bash
set -e

WORKSPACE_FILE="workspace.dsl"
OUTPUT_DIR="architecture/diagrams"

mkdir -p "$OUTPUT_DIR"

echo "==> Валидация DSL"
docker run --rm \
  -v "$(pwd):/usr/local/structurizr" \
  structurizr/cli validate -workspace "$WORKSPACE_FILE"

echo "==> Экспорт в PlantUML"
docker run --rm \
  -v "$(pwd):/usr/local/structurizr" \
  structurizr/cli export -workspace "$WORKSPACE_FILE" -format plantuml -output "$OUTPUT_DIR"

echo "==> Рендер PlantUML в PNG"
for f in "$OUTPUT_DIR"/*.puml; do
  fname=$(basename "$f")
  docker run --rm \
    -v "$(pwd)/$OUTPUT_DIR:/data" \
    plantuml/plantuml -tpng "/data/$fname"
done

echo "==> Готово. Файлы в $OUTPUT_DIR"
ls -la "$OUTPUT_DIR"