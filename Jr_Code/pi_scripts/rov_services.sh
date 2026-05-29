#!/bin/bash

# ========================================
# ROV SERVICE MANAGER
# Easy commands to manage ROV services
# ========================================

case "$1" in
    start)
        echo "🚀 Starting all ROV services..."
        sudo systemctl start rov-sensors rov-mavproxy rov-camera0 rov-camera1
        echo "✅ Services started"
        ;;
        
    stop)
        echo "⏹️  Stopping all ROV services..."
        sudo systemctl stop rov-sensors rov-mavproxy rov-camera0 rov-camera1
        echo "✅ Services stopped"
        ;;
        
    restart)
        echo "🔄 Restarting all ROV services..."
        sudo systemctl restart rov-sensors rov-mavproxy rov-camera0 rov-camera1
        echo "✅ Services restarted"
        ;;
        
    status)
        echo "📊 ROV Service Status:"
        echo "===================="
        systemctl is-active rov-sensors && echo "✅ Sensors:  Running" || echo "❌ Sensors:  Stopped"
        systemctl is-active rov-mavproxy && echo "✅ MAVProxy: Running" || echo "❌ MAVProxy: Stopped"
        systemctl is-active rov-camera0 && echo "✅ Camera 0: Running" || echo "❌ Camera 0: Stopped"
        systemctl is-active rov-camera1 && echo "✅ Camera 1: Running" || echo "❌ Camera 1: Stopped"
        ;;
        
    logs)
        SERVICE="${2:-rov-sensors}"
        echo "📋 Viewing logs for $SERVICE (Ctrl+C to exit)..."
        sudo journalctl -u "$SERVICE" -f
        ;;
        
    enable)
        echo "✅ Enabling auto-start on boot..."
        sudo systemctl enable rov-sensors rov-mavproxy rov-camera0 rov-camera1
        echo "✅ Services will start automatically on boot"
        ;;
        
    disable)
        echo "⏸️  Disabling auto-start on boot..."
        sudo systemctl disable rov-sensors rov-mavproxy rov-camera0 rov-camera1
        echo "✅ Services will NOT start automatically on boot"
        ;;
        
    *)
        echo "===========================================" 
        echo "🤖 ROV SERVICE MANAGER"
        echo "==========================================="
        echo ""
        echo "Usage: ./rov_services.sh [command]"
        echo ""
        echo "Commands:"
        echo "  start      - Start all services"
        echo "  stop       - Stop all services"
        echo "  restart    - Restart all services"
        echo "  status     - Show service status"
        echo "  logs       - View service logs (default: sensors)"
        echo "              ./rov_services.sh logs rov-mavproxy"
        echo "  enable     - Enable auto-start on boot"
        echo "  disable    - Disable auto-start"
        echo ""
        echo "Examples:"
        echo "  ./rov_services.sh start"
        echo "  ./rov_services.sh status"
        echo "  ./rov_services.sh logs rov-sensors"
        echo ""
        exit 1
        ;;
esac
