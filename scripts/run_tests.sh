#!/bin/bash

# Script pour exécuter les tests SmartPy

echo "=========================================="
echo "Fractional Art Marketplace - Test Runner"
echo "=========================================="
echo ""

# Vérifier si SmartPy est installé
if ! command -v SmartPy.sh &> /dev/null
then
    echo "⚠️  SmartPy n'est pas installé"
    echo "Installation de SmartPy..."
    sh <(curl -s https://smartpy.io/cli/install.sh)
fi

echo "📋 Exécution des tests..."
echo ""

# Exécuter les tests
~/smartpy-cli/SmartPy.sh test test_contracts.py /tmp/smartpy_output

echo ""
echo "=========================================="
echo "✅ Tests terminés!"
echo "=========================================="
echo ""
echo "Résultats disponibles dans : /tmp/smartpy_output"
echo "Ouvrez /tmp/smartpy_output/index.html dans un navigateur pour voir les résultats détaillés"
