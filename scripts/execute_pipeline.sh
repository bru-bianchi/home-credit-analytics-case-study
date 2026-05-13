set -e

echo "Executando scripts sequencialmente..."

for script in $(find scripts -maxdepth 1 -type f -name "*.py" | sort); do
  echo "Executando: $script"
  python "$script"
done

echo "Pipeline finalizado."