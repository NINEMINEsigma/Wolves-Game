import asyncio
import logging
from pathlib import Path
from aiohttp import web, WSMsgType
from aiohttp.web import StaticResource
from Convention.Convention.Runtime.GlobalConfig import ProjectConfig

from .websocket_server import WebSocketServer
from .event_recorder import EventRecorder
from .replay_system import ReplaySystem
from .web_ui_system import WebUISystem

__logger__ = logging.getLogger(__name__)

class WebServer:
    def __init__(self):
        self.config = ProjectConfig()
        self.web_config = self.config.FindItem("web", {})
        
        # 创建组件
        self.websocket_server = WebSocketServer(
            host=self.web_config.get("websocket_host", "localhost"),
            port=self.web_config.get("websocket_port", 8765)
        )
        self.event_recorder = EventRecorder(
            log_file=self.web_config.get("event_log_path", "logs/game_events.json")
        )
        self.replay_system = ReplaySystem(self.event_recorder, self.websocket_server)
        self.web_ui_system = WebUISystem(self.websocket_server, self.event_recorder)
        
        # 创建aiohttp应用
        self.app = web.Application()
        self.setup_routes()
        
    def setup_routes(self):
        """设置路由"""
        # 静态文件服务
        static_path = self.web_config.get("static_files_path", "src/web/static")
        static_resource = StaticResource(static_path)
        self.app.router.add_static('/static', static_resource)
        
        # 主页
        self.app.router.add_get('/', self.index_handler)
        
        # WebSocket路由
        self.app.router.add_get('/ws', self.websocket_handler)
        
        # API路由
        self.app.router.add_get('/api/status', self.status_handler)
        self.app.router.add_get('/api/game-state', self.game_state_handler)
        self.app.router.add_get('/api/replay-list', self.replay_list_handler)
        
    async def index_handler(self, request):
        """主页处理器"""
        static_path = Path(self.web_config.get("static_files_path", "src/web/static"))
        index_file = static_path / "index.html"
        
        if index_file.exists():
            return web.FileResponse(index_file)
        else:
            return web.Response(
                text="<h1>AI狼人杀游戏</h1><p>静态文件未找到，请检查配置</p>",
                content_type='text/html'
            )
            
    async def websocket_handler(self, request):
        """WebSocket处理器"""
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        
        # 将WebSocket连接传递给WebSocketServer处理
        await self.websocket_server._handle_connection(ws, request.path)
        
        return ws
        
    async def status_handler(self, request):
        """状态API处理器"""
        status = {
            "server_status": "running",
            "websocket_connections": self.websocket_server.get_observer_count(),
            "total_events": len(self.event_recorder.events),
            "game_duration": self.event_recorder.get_game_summary().get("duration", 0)
        }
        return web.json_response(status)
        
    async def game_state_handler(self, request):
        """游戏状态API处理器"""
        game_state = await self.web_ui_system.get_game_state()
        return web.json_response(game_state)
        
    async def replay_list_handler(self, request):
        """回放列表API处理器"""
        replays = await self.replay_system.get_available_replays()
        return web.json_response(replays)
        
    async def start(self, host="localhost", port=8080):
        """启动Web服务器"""
        runner = web.AppRunner(self.app)
        await runner.setup()
        
        site = web.TCPSite(runner, host, port)
        await site.start()
        
        __logger__.info(f"Web服务器启动在 http://{host}:{port}")
        __logger__.info(f"WebSocket服务器启动在 ws://{host}:{self.websocket_server.port}")
        
        # 保持服务器运行
        try:
            await asyncio.Future()  # 无限等待
        except KeyboardInterrupt:
            __logger__.info("正在关闭Web服务器...")
        finally:
            await runner.cleanup()
            
    def get_web_ui_system(self):
        """获取Web UI系统实例"""
        return self.web_ui_system
        
    def get_event_recorder(self):
        """获取事件录制器实例"""
        return self.event_recorder
        
    def get_replay_system(self):
        """获取回放系统实例"""
        return self.replay_system

async def main():
    """主函数"""
    server = WebServer()
    
    # 从配置获取服务器设置
    config = ProjectConfig()
    web_config = config.FindItem("web", {})
    
    host = web_config.get("http_host", "localhost")
    port = web_config.get("http_port", 8080)
    
    await server.start(host, port)

if __name__ == "__main__":
    # 设置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # 运行服务器
    asyncio.run(main()) 