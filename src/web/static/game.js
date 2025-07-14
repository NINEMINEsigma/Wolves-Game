// 游戏客户端类
class GameClient {
    constructor() {
        this.websocket = null;
        this.observerId = null;
        this.isConnected = false;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        this.reconnectDelay = 2000;
        this.gameState = {
            currentRound: 0,
            currentPhase: '',
            alivePlayers: [],
            deadPlayers: [],
            totalEvents: 0,
            observerCount: 0
        };
        this.chatHistory = [];
        this.replayMode = false;
        
        this.initializeElements();
        this.bindEvents();
        this.connect();
    }
    
    // 初始化DOM元素引用
    initializeElements() {
        // 游戏状态元素
        this.elements = {
            currentRound: document.getElementById('current-round'),
            currentPhase: document.getElementById('current-phase'),
            observerCount: document.getElementById('observer-count'),
            aliveCount: document.getElementById('alive-count'),
            deadCount: document.getElementById('dead-count'),
            alivePlayersList: document.getElementById('alive-players-list'),
            deadPlayersList: document.getElementById('dead-players-list'),
            totalEvents: document.getElementById('total-events'),
            gameDuration: document.getElementById('game-duration'),
            
            // 聊天相关
            chatHistory: document.getElementById('chat-history'),
            clearChat: document.getElementById('clear-chat'),
            exportChat: document.getElementById('export-chat'),
            
            // 回放控制
            startReplay: document.getElementById('start-replay'),
            pauseReplay: document.getElementById('pause-replay'),
            resumeReplay: document.getElementById('resume-replay'),
            stopReplay: document.getElementById('stop-replay'),
            playbackSpeed: document.getElementById('playback-speed'),
            sequenceJump: document.getElementById('sequence-jump'),
            jumpToSequence: document.getElementById('jump-to-sequence'),
            replayStatus: document.getElementById('replay-status'),
            currentSequence: document.getElementById('current-sequence'),
            totalSequence: document.getElementById('total-sequence'),
            
            // 连接状态
            connectionIndicator: document.getElementById('connection-indicator'),
            connectionStatus: document.getElementById('connection-status'),
            observerId: document.getElementById('observer-id'),
            
            // 模态框和加载
            modal: document.getElementById('modal'),
            modalTitle: document.getElementById('modal-title'),
            modalBody: document.getElementById('modal-body'),
            loading: document.getElementById('loading')
        };
    }
    
    // 绑定事件监听器
    bindEvents() {
        // 聊天控制
        this.elements.clearChat.addEventListener('click', () => this.clearChatHistory());
        this.elements.exportChat.addEventListener('click', () => this.exportChatHistory());
        
        // 回放控制
        this.elements.startReplay.addEventListener('click', () => this.startReplay());
        this.elements.pauseReplay.addEventListener('click', () => this.pauseReplay());
        this.elements.resumeReplay.addEventListener('click', () => this.resumeReplay());
        this.elements.stopReplay.addEventListener('click', () => this.stopReplay());
        this.elements.jumpToSequence.addEventListener('click', () => this.jumpToSequence());
        this.elements.playbackSpeed.addEventListener('change', (e) => this.changePlaybackSpeed(e.target.value));
        
        // 模态框关闭
        document.querySelector('.close').addEventListener('click', () => this.closeModal());
        window.addEventListener('click', (e) => {
            if (e.target === this.elements.modal) {
                this.closeModal();
            }
        });
        
        // 页面卸载时清理
        window.addEventListener('beforeunload', () => this.disconnect());
    }
    
    // 连接WebSocket
    connect() {
        try {
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            const host = window.location.hostname;
            const port = window.location.port || '8080';
            const wsUrl = `${protocol}//${host}:${port}/ws`;
            
            this.websocket = new WebSocket(wsUrl);
            
            this.websocket.onopen = () => this.onConnectionOpen();
            this.websocket.onmessage = (event) => this.onMessage(event);
            this.websocket.onclose = () => this.onConnectionClose();
            this.websocket.onerror = (error) => this.onConnectionError(error);
            
        } catch (error) {
            console.error('WebSocket连接失败:', error);
            this.showError('连接失败', '无法连接到游戏服务器');
        }
    }
    
    // 连接建立
    onConnectionOpen() {
        this.isConnected = true;
        this.reconnectAttempts = 0;
        this.updateConnectionStatus('已连接', true);
        this.elements.loading.classList.add('hidden');
        
        console.log('WebSocket连接已建立');
    }
    
    // 接收消息
    onMessage(event) {
        try {
            const data = JSON.parse(event.data);
            this.handleMessage(data);
        } catch (error) {
            console.error('解析消息失败:', error);
        }
    }
    
    // 处理不同类型的消息
    handleMessage(data) {
        switch (data.type) {
            case 'connection_established':
                this.observerId = data.observer_id;
                this.elements.observerId.textContent = data.observer_id;
                break;
                
            case 'game_event':
                this.handleGameEvent(data.event_type, data.data);
                break;
                
            case 'game_state':
                this.updateGameState(data.data);
                break;
                
            case 'replay_started':
                this.onReplayStarted(data);
                break;
                
            case 'replay_paused':
                this.onReplayPaused(data);
                break;
                
            case 'replay_resumed':
                this.onReplayResumed(data);
                break;
                
            case 'replay_stopped':
                this.onReplayStopped(data);
                break;
                
            case 'replay_event':
                this.handleReplayEvent(data.event);
                break;
                
            case 'replay_completed':
                this.onReplayCompleted(data);
                break;
                
            case 'replay_error':
                this.showError('回放错误', data.message);
                break;
                
            case 'pong':
                // 心跳响应，可以用于延迟检测
                break;
                
            default:
                console.log('未知消息类型:', data.type);
        }
    }
    
    // 处理游戏事件
    handleGameEvent(eventType, data) {
        switch (eventType) {
            case 'title':
                this.updateTitle(data);
                break;
                
            case 'phase':
                this.updatePhase(data);
                break;
                
            case 'public_speech':
                this.addChatMessage(data, 'public');
                break;
                
            case 'private_speech':
                this.addChatMessage(data, 'private');
                break;
                
            case 'system_message':
                this.addChatMessage(data, 'system');
                break;
                
            case 'player_status_update':
                this.updatePlayerStatus(data);
                break;
                
            case 'game_victory':
                this.handleGameVictory(data);
                break;
                
            case 'vote_result':
                this.handleVoteResult(data);
                break;
                
            case 'night_action':
                this.handleNightAction(data);
                break;
                
            default:
                console.log('未知游戏事件类型:', eventType);
        }
    }
    
    // 更新游戏标题
    updateTitle(data) {
        this.elements.currentRound.textContent = data.title;
        this.gameState.currentRound = data.round;
    }
    
    // 更新游戏阶段
    updatePhase(data) {
        this.elements.currentPhase.textContent = data.phase;
        this.gameState.currentPhase = data.phase;
    }
    
    // 添加聊天消息
    addChatMessage(data, type) {
        const timestamp = new Date().toLocaleTimeString();
        const messageDiv = document.createElement('div');
        messageDiv.className = `chat-message ${type}`;
        
        let content = `<span class="timestamp">[${timestamp}]</span>`;
        
        if (type === 'public' || type === 'private') {
            content += `<span class="speaker">${data.playerId}(${data.role})</span>`;
            content += `<span class="message">${data.message}</span>`;
        } else if (type === 'system') {
            content += `<span class="message">${data.message}</span>`;
        }
        
        messageDiv.innerHTML = content;
        this.elements.chatHistory.appendChild(messageDiv);
        this.elements.chatHistory.scrollTop = this.elements.chatHistory.scrollHeight;
        
        // 保存到历史记录
        this.chatHistory.push({
            timestamp: new Date(),
            type: type,
            data: data
        });
    }
    
    // 更新玩家状态
    updatePlayerStatus(data) {
        this.gameState.alivePlayers = data.alive_players;
        this.gameState.deadPlayers = data.dead_players;
        
        this.elements.aliveCount.textContent = data.total_alive;
        this.elements.deadCount.textContent = data.total_dead;
        
        this.renderPlayerList(this.elements.alivePlayersList, data.alive_players, false);
        this.renderPlayerList(this.elements.deadPlayersList, data.dead_players, true);
    }
    
    // 渲染玩家列表
    renderPlayerList(container, players, isDead) {
        container.innerHTML = '';
        
        players.forEach(player => {
            const playerCard = document.createElement('div');
            playerCard.className = `player-card ${isDead ? 'dead' : ''}`;
            
            playerCard.innerHTML = `
                <div class="player-name">${player.playerId}</div>
                <div class="player-role">${player.role}</div>
                ${isDead && player.cause_of_death ? `<div class="death-cause">${player.cause_of_death}</div>` : ''}
            `;
            
            container.appendChild(playerCard);
        });
    }
    
    // 处理游戏胜利
    handleGameVictory(data) {
        this.addChatMessage({
            message: `🏆 ${data.victory_condition}`
        }, 'system');
        
        this.showModal('游戏结束', `
            <div style="text-align: center; padding: 20px;">
                <h3 style="color: #27ae60; margin-bottom: 15px;">${data.victory_condition}</h3>
                <p>游戏已结束，感谢观看！</p>
            </div>
        `);
    }
    
    // 处理投票结果
    handleVoteResult(data) {
        const voteText = Object.entries(data.vote_data)
            .map(([player, votes]) => `${player}: ${votes}票`)
            .join(', ');
            
        this.addChatMessage({
            message: `🗳️ 投票结果: ${voteText} → ${data.result}`
        }, 'system');
    }
    
    // 处理夜晚行动
    handleNightAction(data) {
        this.addChatMessage({
            message: `🌙 ${data.player_id} 对 ${data.target_id} 使用 ${data.action_type}: ${data.result}`
        }, 'system');
    }
    
    // 更新游戏状态
    updateGameState(state) {
        this.gameState = { ...this.gameState, ...state };
        this.elements.totalEvents.textContent = state.total_events;
        this.elements.observerCount.textContent = state.observer_count;
    }
    
    // 回放控制方法
    startReplay() {
        if (!this.isConnected) return;
        
        const speed = parseFloat(this.elements.playbackSpeed.value);
        this.sendMessage({
            type: 'request_replay',
            action: 'start',
            speed: speed
        });
        
        this.replayMode = true;
        this.updateReplayControls();
    }
    
    pauseReplay() {
        this.sendMessage({
            type: 'request_replay',
            action: 'pause'
        });
    }
    
    resumeReplay() {
        this.sendMessage({
            type: 'request_replay',
            action: 'resume'
        });
    }
    
    stopReplay() {
        this.sendMessage({
            type: 'request_replay',
            action: 'stop'
        });
        
        this.replayMode = false;
        this.updateReplayControls();
    }
    
    jumpToSequence() {
        const sequence = parseInt(this.elements.sequenceJump.value);
        if (isNaN(sequence) || sequence < 0) {
            this.showError('输入错误', '请输入有效的序列号');
            return;
        }
        
        this.sendMessage({
            type: 'request_replay',
            action: 'jump',
            sequence: sequence
        });
    }
    
    changePlaybackSpeed(speed) {
        this.sendMessage({
            type: 'request_replay',
            action: 'speed',
            speed: parseFloat(speed)
        });
    }
    
    // 回放事件处理
    onReplayStarted(data) {
        this.elements.replayStatus.textContent = '播放中';
        this.elements.totalSequence.textContent = data.total_events;
        this.updateReplayControls();
    }
    
    onReplayPaused(data) {
        this.elements.replayStatus.textContent = '已暂停';
        this.elements.currentSequence.textContent = data.current_sequence;
        this.updateReplayControls();
    }
    
    onReplayResumed(data) {
        this.elements.replayStatus.textContent = '播放中';
        this.updateReplayControls();
    }
    
    onReplayStopped(data) {
        this.elements.replayStatus.textContent = '已停止';
        this.elements.currentSequence.textContent = '0';
        this.replayMode = false;
        this.updateReplayControls();
    }
    
    onReplayCompleted(data) {
        this.elements.replayStatus.textContent = '播放完成';
        this.elements.currentSequence.textContent = data.total_events;
        this.replayMode = false;
        this.updateReplayControls();
    }
    
    handleReplayEvent(event) {
        // 在回放模式下处理事件
        this.handleGameEvent(event.event_type, event.data);
        this.elements.currentSequence.textContent = event.sequence_id;
    }
    
    // 更新回放控制按钮状态
    updateReplayControls() {
        const isReplaying = this.replayMode;
        
        this.elements.startReplay.disabled = isReplaying;
        this.elements.pauseReplay.disabled = !isReplaying;
        this.elements.resumeReplay.disabled = !isReplaying;
        this.elements.stopReplay.disabled = !isReplaying;
    }
    
    // 聊天历史控制
    clearChatHistory() {
        if (confirm('确定要清空聊天记录吗？')) {
            this.elements.chatHistory.innerHTML = '';
            this.chatHistory = [];
        }
    }
    
    exportChatHistory() {
        const chatText = this.chatHistory.map(entry => {
            const timestamp = entry.timestamp.toLocaleString();
            if (entry.type === 'public' || entry.type === 'private') {
                return `[${timestamp}] ${entry.data.playerId}(${entry.data.role}): ${entry.data.message}`;
            } else {
                return `[${timestamp}] 系统: ${entry.data.message}`;
            }
        }).join('\n');
        
        const blob = new Blob([chatText], { type: 'text/plain;charset=utf-8' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `狼人杀游戏记录_${new Date().toISOString().slice(0, 19)}.txt`;
        a.click();
        URL.revokeObjectURL(url);
    }
    
    // 连接状态管理
    updateConnectionStatus(status, connected = false) {
        this.elements.connectionStatus.textContent = status;
        this.elements.connectionIndicator.className = `status-indicator ${connected ? 'connected' : ''}`;
    }
    
    onConnectionClose() {
        this.isConnected = false;
        this.updateConnectionStatus('连接断开', false);
        
        if (this.reconnectAttempts < this.maxReconnectAttempts) {
            this.reconnectAttempts++;
            this.updateConnectionStatus(`正在重连... (${this.reconnectAttempts}/${this.maxReconnectAttempts})`, false);
            
            setTimeout(() => this.connect(), this.reconnectDelay);
        } else {
            this.updateConnectionStatus('连接失败', false);
            this.showError('连接失败', '无法连接到游戏服务器，请刷新页面重试');
        }
    }
    
    onConnectionError(error) {
        console.error('WebSocket连接错误:', error);
        this.updateConnectionStatus('连接错误', false);
    }
    
    // 发送消息
    sendMessage(data) {
        if (this.websocket && this.websocket.readyState === WebSocket.OPEN) {
            this.websocket.send(JSON.stringify(data));
        } else {
            console.error('WebSocket未连接');
        }
    }
    
    // 断开连接
    disconnect() {
        if (this.websocket) {
            this.websocket.close();
        }
    }
    
    // 显示模态框
    showModal(title, content) {
        this.elements.modalTitle.textContent = title;
        this.elements.modalBody.innerHTML = content;
        this.elements.modal.style.display = 'block';
    }
    
    // 关闭模态框
    closeModal() {
        this.elements.modal.style.display = 'none';
    }
    
    // 显示错误
    showError(title, message) {
        this.showModal(title, `
            <div style="color: #e74c3c; text-align: center; padding: 20px;">
                <p>${message}</p>
            </div>
        `);
    }
    
    // 心跳检测
    startHeartbeat() {
        setInterval(() => {
            if (this.isConnected) {
                this.sendMessage({ type: 'ping' });
            }
        }, 30000); // 每30秒发送一次心跳
    }
}

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', () => {
    window.gameClient = new GameClient();
    window.gameClient.startHeartbeat();
}); 