from src.engine.game_engine import *
from src.engine.player_engine import *
from src.web.web_ui_system import WebUISystem
from src.web.websocket_server import WebSocketServer
from src.web.event_recorder import EventRecorder
from src.web.replay_system import ReplaySystem
import asyncio
import threading
from aiohttp import web
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 创建Web组件
__WebSocketServer = WebSocketServer()
__EventRecorder = EventRecorder()
__ReplaySystem = ReplaySystem(__EventRecorder, __WebSocketServer)
# 使用Web UI系统替换原有的UISystem
__WebUISystem = WebUISystem(__WebSocketServer, __EventRecorder)
logger.info(f"WebUISystem.__init__: event_queue id={id(__WebSocketServer.event_queue) if hasattr(__WebSocketServer, 'event_queue') else 'N/A'}")
__GameController = GameController()
__DaySystem = DaySystem()
__NightSystem = NightSystem()
__PublicMemory = PublicMemory()

class GameEntry:
    def __init__(self):
        # 创建事件队列用于游戏逻辑和Web服务器之间的通信
        self.event_queue = asyncio.Queue()
        logger.info(f"GameEntry.__init__: event_queue id={id(self.event_queue)}, event_loop id={id(asyncio.get_event_loop())}")
        # 创建连接等待事件
        self.connection_event = asyncio.Event()
        # 创建HTTP应用
        self.app = web.Application()
        self.setup_http_routes()
        
    def setup_http_routes(self):
        """设置HTTP路由"""
        # 静态文件服务
        static_path = Path("src/web/static")
        self.app.router.add_static('/static', static_path)
        
        # 主页
        self.app.router.add_get('/', self.index_handler)
        
        # WebSocket路由
        self.app.router.add_get('/ws', self.websocket_handler)
        
        # API路由
        self.app.router.add_get('/api/status', self.status_handler)
        self.app.router.add_get('/api/game-state', self.game_state_handler)
        
    async def index_handler(self, request):
        """主页处理器"""
        index_file = Path("src/web/static/index.html")
        if index_file.exists():
            return web.FileResponse(index_file)
        else:
            return web.Response(
                text="<h1>AI狼人杀游戏</h1><p>静态文件未找到</p>",
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
            "total_events": len(self.event_recorder.events)
        }
        return web.json_response(status)
        
    async def game_state_handler(self, request):
        """游戏状态API处理器"""
        game_state = await self.web_ui_system.get_game_state()
        return web.json_response(game_state)
        
    @property
    def websocket_server(self) -> WebSocketServer:
        return Architecture.Get(WebSocketServer)

    @property
    def event_recorder(self) -> EventRecorder:
        return Architecture.Get(EventRecorder)

    @property
    def replay_system(self) -> ReplaySystem:
        return Architecture.Get(ReplaySystem)
        
    @property
    def web_ui_system(self) -> WebUISystem:
        return Architecture.Get(WebUISystem)
                
    async def start_web_server(self):
        """启动Web服务器"""
        logger.info("start_web_server called")
        # 设置事件队列和连接事件
        self.websocket_server.set_event_queue(self.event_queue)
        self.websocket_server.set_connection_event(self.connection_event)
        
        # 启动HTTP服务器
        runner = web.AppRunner(self.app)
        await runner.setup()
        
        site = web.TCPSite(runner, "localhost", 8080)
        await site.start()
        
        print("HTTP服务器启动在 http://localhost:8080")
        print("WebSocket服务器启动在 ws://localhost:8765")
        
    async def wait_for_connection(self):
        """等待至少一个用户连接"""
        logger.info("wait_for_connection called")
        print("等待用户连接...")
        await self.connection_event.wait()
        print(f"用户已连接，开始游戏。当前连接数: {self.websocket_server.get_observer_count()}")
        
    async def run_game_logic(self):
        """在事件循环中运行异步游戏逻辑"""
        logger.info("run_game_logic called")
        config = ProjectConfig()
        # 配置游戏房间
        room:Dict[str,int] = config.FindItem("room")
        game:GameController = Architecture.Get(GameController)
        # 开始记录游戏事件
        self.event_recorder.start_game()
        playerId:int = 1
        for playerRole,playerCount in room.items():
            for i in range(playerCount):
                game.add_player(PlayerAgent.create(f"player{playerId}",playerRole))
                playerId += 1
        # 开始游戏（假设start_game可以异步执行，否则直接调用）
        if hasattr(game, 'start_game') and callable(getattr(game, 'start_game')):
            result = game.start_game()
            if hasattr(result, '__await__'):
                await result
        # 游戏结束后保存事件
        self.event_recorder.end_game()
        
    async def start(self) -> None:
        """异步启动游戏"""
        logger.info("GameEntry.start called")
        try:
            # 启动Web服务器
            await self.start_web_server()
            # 等待至少一个用户连接
            await self.wait_for_connection()
            # 同时运行游戏逻辑和消息处理
            await asyncio.gather(
                self.run_game_logic(),
                self.websocket_server.process_event_queue()
            )
        except Exception as e:
            logger.exception(f"asyncio.gather or start failed: {e}")

entry:GameEntry = GameEntry()

Architecture.RegisterGeneric(
    entry,
     lambda: asyncio.run(entry.start()),
     GameController
     )