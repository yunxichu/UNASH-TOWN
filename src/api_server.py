"""
API服务层 - 提供HTTP接口供外部智能体接入
"""
import json
import threading
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from typing import Dict, Optional, Callable, Any
from dataclasses import dataclass

from .agent_manager import AgentManager, AgentEvent
from .agent_interface import (
    TradingContext, TradingDecision, AgentStatus, AgentType
)


@dataclass
class APIConfig:
    host: str = "0.0.0.0"
    port: int = 8080
    api_key: Optional[str] = None
    cors_enabled: bool = True
    rate_limit: int = 100


class APIRequestHandler(BaseHTTPRequestHandler):
    agent_manager: AgentManager = None
    api_config: APIConfig = None
    exchange_engine: Any = None
    
    def log_message(self, format, *args):
        pass
    
    def send_json_response(self, data: Dict, status: int = 200):
        response = json.dumps(data, ensure_ascii=False)
        
        headers = {"Content-Type": "application/json"}
        if self.api_config.cors_enabled:
            headers["Access-Control-Allow-Origin"] = "*"
            headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
            headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
        
        self.send_response(status)
        for key, value in headers.items():
            self.send_header(key, value)
        self.end_headers()
        self.wfile.write(response.encode("utf-8"))
    
    def do_OPTIONS(self):
        if self.api_config.cors_enabled:
            self.send_response(200)
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
            self.end_headers()
        else:
            self.send_response(405)
            self.end_headers()
    
    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        
        if not self._check_auth():
            self.send_json_response({"error": "Unauthorized"}, 401)
            return
        
        if path == "/api/health":
            self._handle_health()
        elif path == "/api/agents":
            self._handle_list_agents()
        elif path.startswith("/api/agents/"):
            agent_id = path.split("/")[-1]
            self._handle_get_agent(agent_id)
        elif path == "/api/market":
            self._handle_market_status()
        elif path == "/api/leaderboard":
            self._handle_leaderboard()
        elif path == "/api/stats":
            self._handle_stats()
        else:
            self.send_json_response({"error": "Not found"}, 404)
    
    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path
        
        if not self._check_auth():
            self.send_json_response({"error": "Unauthorized"}, 401)
            return
        
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length).decode("utf-8") if content_length > 0 else "{}"
        
        try:
            data = json.loads(body) if body else {}
        except json.JSONDecodeError:
            self.send_json_response({"error": "Invalid JSON"}, 400)
            return
        
        if path == "/api/agents/register":
            self._handle_register_agent(data)
        elif path == "/api/agents/unregister":
            self._handle_unregister_agent(data)
        elif path.startswith("/api/agents/") and path.endswith("/activate"):
            agent_id = path.split("/")[3]
            self._handle_activate_agent(agent_id)
        elif path.startswith("/api/agents/") and path.endswith("/deactivate"):
            agent_id = path.split("/")[3]
            self._handle_deactivate_agent(agent_id)
        elif path == "/api/decide":
            self._handle_decide(data)
        elif path == "/api/trade/execute":
            self._handle_execute_trade(data)
        elif path == "/api/simulation/start":
            self._handle_start_simulation(data)
        elif path == "/api/simulation/stop":
            self._handle_stop_simulation()
        else:
            self.send_json_response({"error": "Not found"}, 404)
    
    def _check_auth(self) -> bool:
        if not self.api_config.api_key:
            return True
        
        auth_header = self.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]
            return token == self.api_config.api_key
        
        return False
    
    def _handle_health(self):
        self.send_json_response({
            "status": "healthy",
            "timestamp": time.time(),
            "agents_count": self.agent_manager.agent_count,
            "active_count": self.agent_manager.active_count,
        })
    
    def _handle_list_agents(self):
        agents = []
        for agent in self.agent_manager.get_all_agents():
            info = agent.get_info()
            agents.append(info.to_dict())
        
        self.send_json_response({"agents": agents})
    
    def _handle_get_agent(self, agent_id: str):
        agent = self.agent_manager.get_agent(agent_id)
        if not agent:
            self.send_json_response({"error": "Agent not found"}, 404)
            return
        
        stats = self.agent_manager.get_agent_stats(agent_id)
        self.send_json_response({
            "info": agent.get_info().to_dict(),
            "state": agent.get_state().to_dict(),
            "stats": stats,
        })
    
    def _handle_market_status(self):
        if self.exchange_engine:
            overview = self.exchange_engine.get_market_overview()
            self.send_json_response(overview)
        else:
            self.send_json_response({"error": "Exchange not initialized"}, 503)
    
    def _handle_leaderboard(self):
        leaderboard = self.agent_manager.get_leaderboard()
        self.send_json_response({"leaderboard": leaderboard})
    
    def _handle_stats(self):
        stats = self.agent_manager.get_all_stats()
        self.send_json_response({"stats": stats})
    
    def _handle_register_agent(self, data: Dict):
        try:
            agent_type = data.get("type", "callback")
            name = data.get("name", f"Agent_{int(time.time())}")
            initial_capital = data.get("initial_capital", 10000.0)
            
            if agent_type == "remote":
                endpoint = data.get("endpoint")
                if not endpoint:
                    self.send_json_response({"error": "endpoint required for remote agent"}, 400)
                    return
                
                agent_id = self.agent_manager.create_remote_agent(
                    name=name,
                    endpoint=endpoint,
                    initial_capital=initial_capital,
                    api_key=data.get("api_key")
                )
            else:
                agent_id = self.agent_manager.create_callback_agent(
                    name=name,
                    initial_capital=initial_capital,
                    capabilities=data.get("capabilities", []),
                    metadata=data.get("metadata", {})
                )
            
            self.send_json_response({
                "agent_id": agent_id,
                "message": "Agent registered successfully"
            })
        except Exception as e:
            self.send_json_response({"error": str(e)}, 400)
    
    def _handle_unregister_agent(self, data: Dict):
        agent_id = data.get("agent_id")
        if not agent_id:
            self.send_json_response({"error": "agent_id required"}, 400)
            return
        
        success = self.agent_manager.unregister_agent(agent_id)
        if success:
            self.send_json_response({"message": "Agent unregistered"})
        else:
            self.send_json_response({"error": "Agent not found"}, 404)
    
    def _handle_activate_agent(self, agent_id: str):
        success = self.agent_manager.activate_agent(agent_id)
        if success:
            self.send_json_response({"message": "Agent activated"})
        else:
            self.send_json_response({"error": "Agent not found"}, 404)
    
    def _handle_deactivate_agent(self, agent_id: str):
        success = self.agent_manager.deactivate_agent(agent_id)
        if success:
            self.send_json_response({"message": "Agent deactivated"})
        else:
            self.send_json_response({"error": "Agent not found"}, 404)
    
    def _handle_decide(self, data: Dict):
        agent_id = data.get("agent_id")
        context_data = data.get("context", {})
        
        agent = self.agent_manager.get_agent(agent_id)
        if not agent:
            self.send_json_response({"error": "Agent not found"}, 404)
            return
        
        try:
            context = TradingContext(
                market_data=context_data.get("market_data", {}),
                technical=context_data.get("technical", {}),
                agent_state=context_data.get("agent_state", {}),
                order_book_depth=context_data.get("order_book_depth", {}),
                timestamp=context_data.get("timestamp", 0)
            )
            
            decision = agent.decide(context)
            self.agent_manager.record_decision(agent_id)
            
            self.send_json_response(decision.to_dict())
        except Exception as e:
            self.agent_manager.record_error(agent_id, str(e))
            self.send_json_response({"error": str(e)}, 500)
    
    def _handle_execute_trade(self, data: Dict):
        self.send_json_response({"message": "Trade execution handled by exchange"})
    
    def _handle_start_simulation(self, data: Dict):
        self.send_json_response({"message": "Simulation control via main process"})
    
    def _handle_stop_simulation(self):
        self.send_json_response({"message": "Simulation control via main process"})


class APIServer:
    def __init__(
        self,
        agent_manager: AgentManager,
        config: Optional[APIConfig] = None,
        exchange_engine: Any = None
    ):
        self.agent_manager = agent_manager
        self.config = config or APIConfig()
        self.exchange_engine = exchange_engine
        self._server: Optional[HTTPServer] = None
        self._thread: Optional[threading.Thread] = None
        self._running = False
    
    def start(self):
        if self._running:
            return
        
        APIRequestHandler.agent_manager = self.agent_manager
        APIRequestHandler.api_config = self.config
        APIRequestHandler.exchange_engine = self.exchange_engine
        
        self._server = HTTPServer(
            (self.config.host, self.config.port),
            APIRequestHandler
        )
        
        self._running = True
        self._thread = threading.Thread(target=self._run_server, daemon=True)
        self._thread.start()
    
    def _run_server(self):
        print(f"API Server started on {self.config.host}:{self.config.port}")
        while self._running:
            try:
                self._server.handle_request()
            except Exception:
                pass
    
    def stop(self):
        self._running = False
        if self._server:
            self._server.shutdown()
            self._server = None
    
    def set_exchange(self, exchange_engine: Any):
        self.exchange_engine = exchange_engine
        APIRequestHandler.exchange_engine = exchange_engine
    
    @property
    def is_running(self) -> bool:
        return self._running
    
    @property
    def url(self) -> str:
        return f"http://{self.config.host}:{self.config.port}"


def create_api_server(
    agent_manager: AgentManager,
    port: int = 8080,
    api_key: Optional[str] = None
) -> APIServer:
    config = APIConfig(port=port, api_key=api_key)
    return APIServer(agent_manager, config)
