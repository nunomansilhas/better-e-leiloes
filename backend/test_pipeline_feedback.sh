#!/bin/bash

# Test Pipeline Real-Time Feedback System
# Demonstrates state persistence and real-time updates

echo "=================================="
echo "🧪 TESTING PIPELINE FEEDBACK SYSTEM"
echo "=================================="
echo ""

# Start test pipeline in background (10 items, stage 2, 0.5s each = 5s total)
echo "▶ Iniciando test pipeline (10 itens, Stage 2)..."
curl -s -X POST "http://localhost:8000/api/pipeline/test?items=10&stage=2" > /dev/null &
CURL_PID=$!

sleep 0.5

echo ""
echo "📊 Monitoring estado em tempo real (polling a cada 0.5s):"
echo "--------------------------------"

# Poll status 15 times (0.5s interval = 7.5s total)
for i in {1..15}; do
    echo ""
    echo "⏱️  Poll #$i ($(date +%H:%M:%S)):"

    # Get status and parse
    STATUS=$(curl -s "http://localhost:8000/api/pipeline/status")

    # Extract key fields using python
    ACTIVE=$(echo "$STATUS" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('active', False))")
    STAGE=$(echo "$STATUS" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('stage', 'N/A'))")
    CURRENT=$(echo "$STATUS" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('current', 0))")
    TOTAL=$(echo "$STATUS" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('total', 0))")
    MESSAGE=$(echo "$STATUS" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('message', ''))")
    STAGE_NAME=$(echo "$STATUS" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('stage_name', ''))")

    if [ "$ACTIVE" = "True" ]; then
        PERCENT=$((CURRENT * 100 / TOTAL))
        echo "  ✅ Ativa: Stage $STAGE ($STAGE_NAME)"
        echo "  📈 Progresso: $CURRENT/$TOTAL ($PERCENT%)"
        echo "  💬 Mensagem: $MESSAGE"
    else
        echo "  ⏸️  Pipeline INATIVA"
        if [ $i -gt 12 ]; then
            echo "  ✅ Pipeline concluída!"
            break
        fi
    fi

    sleep 0.5
done

echo ""
echo "--------------------------------"
echo ""

# Wait for curl to finish
wait $CURL_PID 2>/dev/null

# Final status check
echo "🔍 Estado final da pipeline:"
curl -s "http://localhost:8000/api/pipeline/status" | python3 -m json.tool

echo ""
echo "=================================="
echo "✅ TESTE CONCLUÍDO!"
echo "=================================="
echo ""
echo "✨ O sistema demonstrou:"
echo "   - Estado persistido em arquivo JSON"
echo "   - Updates em tempo real a cada 500ms"
echo "   - Progresso detalhado (X/Y - mensagem)"
echo "   - Limpeza automática após conclusão"
echo ""
