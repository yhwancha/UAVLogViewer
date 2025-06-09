<template>
  <div
    v-if="isVisible"
    class="chatbot-popup-overlay"
    @mousedown="handleOverlayClick"
  >
    <div
      class="chatbot-popup"
      ref="popup"
      :style="popupStyle"
      @mousedown.stop
    >
      <!-- Header with drag handle and controls -->
      <div
        class="popup-header"
        @mousedown="startDrag"
        ref="header"
      >
        <div class="popup-title">
          <i class="fas fa-robot"></i>
          Flight Data Chatbot
        </div>
        <div class="popup-controls">
          <button
            class="control-btn minimize-btn"
            @click="toggleMinimize"
            :title="isMinimized ? 'Restore' : 'Minimize'"
          >
            <i :class="isMinimized ? 'fas fa-window-restore' : 'fas fa-window-minimize'"></i>
          </button>
          <button
            class="control-btn close-btn"
            @click="closePopup"
            title="Close"
          >
            <i class="fas fa-times"></i>
          </button>
        </div>
      </div>

      <!-- Chatbot content -->
      <div
        v-if="!isMinimized"
        class="popup-content"
        :style="contentStyle"
      >
        <div class="chat-messages" ref="chatMessages">
          <div v-for="(message, index) in chatMessages" :key="index" class="chat-message" :class="message.type">
            <div class="message-bubble" :class="{ 'loading-message': message.isLoading }">
              <div v-if="message.isLoading" class="loading-spinner">
                <div class="spinner"></div>
              </div>
              <span class="message-text">{{ message.text }}</span>
              <span class="message-time">{{ message.time }}</span>
            </div>
          </div>
        </div>
        <div class="chat-input-container">
          <input
            v-model="currentMessage"
            @keyup.enter="sendMessage"
            :placeholder="uploadingFile ? 'Analyzing flight data...' : 'Ask about flight data...'"
            class="chat-input"
            ref="chatInput"
            :disabled="uploadingFile"
          />
          <button
            @click="sendMessage"
            class="send-button"
            :disabled="!currentMessage.trim() || uploadingFile"
          >
            <i class="fas fa-paper-plane"></i>
          </button>
        </div>
      </div>

      <!-- Resize handles -->
      <div
        v-if="!isMinimized"
        class="resize-handle resize-se"
        @mousedown="(event) => startResize('se', event)"
      ></div>
      <div
        v-if="!isMinimized"
        class="resize-handle resize-s"
        @mousedown="(event) => startResize('s', event)"
      ></div>
      <div
        v-if="!isMinimized"
        class="resize-handle resize-e"
        @mousedown="(event) => startResize('e', event)"
      ></div>
    </div>
  </div>
</template>

<script>
export default {
    name: 'ChatbotPopup',
    props: {
        isVisible: {
            type: Boolean,
            default: false
        },
        chatMessages: {
            type: Array,
            default: () => []
        },
        uploadingFile: {
            type: Boolean,
            default: false
        }
    },
    data () {
        return {
            // Position and size
            position: {
                x: 100,
                y: 100
            },
            size: {
                width: 400,
                height: 500
            },
            isMinimized: false,

            // Dragging state
            isDragging: false,
            dragStart: { x: 0, y: 0 },
            initialPosition: { x: 0, y: 0 },

            // Resizing state
            isResizing: false,
            resizeDirection: '',
            resizeStart: { x: 0, y: 0 },
            initialSize: { width: 0, height: 0 },
            initialPosition2: { x: 0, y: 0 },

            // Chat state
            currentMessage: '',
            sessionId: null
        }
    },
    computed: {
        popupStyle () {
            return {
                left: `${this.position.x}px`,
                top: `${this.position.y}px`,
                width: `${this.size.width}px`,
                height: this.isMinimized ? 'auto' : `${this.size.height}px`,
                minWidth: '300px',
                minHeight: this.isMinimized ? 'auto' : '200px',
                maxWidth: '90vw',
                maxHeight: '90vh'
            }
        },
        contentStyle () {
            return {
                height: `${this.size.height - 40}px` // Subtract header height
            }
        }
    },
    mounted () {
    // Center popup on screen initially
        this.centerPopup()

        // Add event listeners
        document.addEventListener('mousemove', this.handleMouseMove)
        document.addEventListener('mouseup', this.handleMouseUp)

        // Generate session ID
        this.sessionId = 'popup_' + Math.random().toString(36).substr(2, 9)
    },
    beforeDestroy () {
    // Remove event listeners
        document.removeEventListener('mousemove', this.handleMouseMove)
        document.removeEventListener('mouseup', this.handleMouseUp)
    },
    methods: {
        centerPopup () {
            const screenWidth = window.innerWidth
            const screenHeight = window.innerHeight
            this.position.x = (screenWidth - this.size.width) / 2
            this.position.y = (screenHeight - this.size.height) / 2
        },

        closePopup () {
            this.$emit('close')
        },

        toggleMinimize () {
            this.isMinimized = !this.isMinimized
        },

        handleOverlayClick (event) {
            // Close popup when clicking outside
            if (event.target.classList.contains('chatbot-popup-overlay')) {
                this.closePopup()
            }
        },

        // Dragging functionality
        startDrag (event) {
            this.isDragging = true
            this.dragStart.x = event.clientX
            this.dragStart.y = event.clientY
            this.initialPosition.x = this.position.x
            this.initialPosition.y = this.position.y
            event.preventDefault()
        },

        // Resizing functionality
        startResize (direction, event) {
            this.isResizing = true
            this.resizeDirection = direction
            this.resizeStart.x = event.clientX
            this.resizeStart.y = event.clientY
            this.initialSize.width = this.size.width
            this.initialSize.height = this.size.height
            this.initialPosition2.x = this.position.x
            this.initialPosition2.y = this.position.y
            event.preventDefault()
        },

        handleMouseMove (event) {
            if (this.isDragging) {
                const deltaX = event.clientX - this.dragStart.x
                const deltaY = event.clientY - this.dragStart.y

                this.position.x = Math.max(0, Math.min(
                    window.innerWidth - this.size.width,
                    this.initialPosition.x + deltaX
                ))
                this.position.y = Math.max(0, Math.min(
                    window.innerHeight - 40, // Leave space for header
                    this.initialPosition.y + deltaY
                ))
            } else if (this.isResizing) {
                const deltaX = event.clientX - this.resizeStart.x
                const deltaY = event.clientY - this.resizeStart.y

                if (this.resizeDirection.includes('e')) {
                    this.size.width = Math.max(300, Math.min(
                        window.innerWidth - this.position.x,
                        this.initialSize.width + deltaX
                    ))
                }
                if (this.resizeDirection.includes('s')) {
                    this.size.height = Math.max(200, Math.min(
                        window.innerHeight - this.position.y,
                        this.initialSize.height + deltaY
                    ))
                }
            }
        },

        handleMouseUp () {
            this.isDragging = false
            this.isResizing = false
            this.resizeDirection = ''
        },

        // Chat functionality
        async sendMessage () {
            if (!this.currentMessage.trim() || this.uploadingFile) {
                return
            }

            const message = this.currentMessage.trim()
            this.currentMessage = ''

            // Add user message
            this.$emit('send-message', {
                text: message,
                type: 'user',
                time: new Date().toLocaleTimeString(),
                sessionId: this.sessionId
            })

            // Auto-scroll to bottom
            this.$nextTick(() => {
                this.scrollToBottom()
            })
        },

        scrollToBottom () {
            if (this.$refs.chatMessages) {
                this.$refs.chatMessages.scrollTop = this.$refs.chatMessages.scrollHeight
            }
        },

        focusInput () {
            this.$nextTick(() => {
                if (this.$refs.chatInput) {
                    this.$refs.chatInput.focus()
                }
            })
        }
    },
    watch: {
        isVisible (newVal) {
            if (newVal) {
                this.focusInput()
            }
        },
        chatMessages () {
            this.$nextTick(() => {
                this.scrollToBottom()
            })
        }
    }
}
</script>

<style scoped>
.chatbot-popup-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100vw;
  height: 100vh;
  background-color: rgba(0, 0, 0, 0.3);
  z-index: 9999;
  backdrop-filter: blur(2px);
}

.chatbot-popup {
  position: absolute;
  background: white;
  border-radius: 8px;
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.3);
  overflow: hidden;
  border: 1px solid #ddd;
  display: flex;
  flex-direction: column;
}

.popup-header {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  padding: 8px 12px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  cursor: move;
  user-select: none;
  height: 40px;
  box-sizing: border-box;
}

.popup-title {
  display: flex;
  align-items: center;
  font-weight: 600;
  font-size: 14px;
}

.popup-title i {
  margin-right: 8px;
}

.popup-controls {
  display: flex;
  gap: 4px;
}

.control-btn {
  background: rgba(255, 255, 255, 0.2);
  border: none;
  color: white;
  width: 24px;
  height: 24px;
  border-radius: 4px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background-color 0.2s;
}

.control-btn:hover {
  background: rgba(255, 255, 255, 0.3);
}

.close-btn:hover {
  background: rgba(255, 0, 0, 0.6);
}

.popup-content {
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 10px;
  background: #f8f9fa;
  min-height: 0;
}

.chat-message {
  margin-bottom: 12px;
}

.chat-message.user {
  text-align: right;
}

.message-bubble {
  display: inline-block;
  max-width: 85%;
  padding: 8px 12px;
  border-radius: 18px;
  word-wrap: break-word;
  position: relative;
}

.chat-message.user .message-bubble {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  margin-left: auto;
}

.chat-message.assistant .message-bubble {
  background: white;
  border: 1px solid #e0e0e0;
  color: #333;
}

.loading-message {
  opacity: 0.7;
}

.loading-spinner {
  display: inline-block;
  margin-right: 8px;
}

.spinner {
  width: 12px;
  height: 12px;
  border: 2px solid #f3f3f3;
  border-top: 2px solid #667eea;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.message-text {
  display: block;
  margin-bottom: 4px;
  line-height: 1.4;
  white-space: pre-wrap;
}

.message-time {
  font-size: 10px;
  opacity: 0.7;
}

.chat-input-container {
  display: flex;
  padding: 10px;
  background: white;
  border-top: 1px solid #e0e0e0;
  gap: 8px;
}

.chat-input {
  flex: 1;
  padding: 8px 12px;
  border: 1px solid #ddd;
  border-radius: 20px;
  outline: none;
  font-size: 14px;
}

.chat-input:focus {
  border-color: #667eea;
  box-shadow: 0 0 0 2px rgba(102, 126, 234, 0.2);
}

.chat-input:disabled {
  background-color: #f5f5f5;
  color: #999;
}

.send-button {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border: none;
  width: 40px;
  height: 40px;
  border-radius: 50%;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: transform 0.2s;
}

.send-button:hover:not(:disabled) {
  transform: scale(1.05);
}

.send-button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
  transform: none;
}

/* Resize handles */
.resize-handle {
  position: absolute;
  background: transparent;
}

.resize-se {
  bottom: 0;
  right: 0;
  width: 15px;
  height: 15px;
  cursor: se-resize;
}

.resize-s {
  bottom: 0;
  left: 15px;
  right: 15px;
  height: 5px;
  cursor: s-resize;
}

.resize-e {
  top: 40px;
  right: 0;
  width: 5px;
  bottom: 5px;
  cursor: e-resize;
}

.resize-handle:hover {
  background: rgba(102, 126, 234, 0.3);
}

/* Scrollbar styling */
.chat-messages::-webkit-scrollbar {
  width: 6px;
}

.chat-messages::-webkit-scrollbar-track {
  background: #f1f1f1;
  border-radius: 3px;
}

.chat-messages::-webkit-scrollbar-thumb {
  background: #c1c1c1;
  border-radius: 3px;
}

.chat-messages::-webkit-scrollbar-thumb:hover {
  background: #a1a1a1;
}
</style>
