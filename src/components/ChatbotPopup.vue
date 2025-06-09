<template>
  <div
    v-if="isVisible"
    class="chatbot-popup"
    ref="popup"
    :style="popupStyle"
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
          <div class="message-bubble"
               :class="{ 'loading-message': message.isLoading, 'typing-message': message.isTyping }">
            <div v-if="message.isLoading" class="loading-spinner">
              <div class="spinner"></div>
            </div>
            <div v-if="message.isTyping" class="typing-indicator">
              <span class="typing-dot"></span>
              <span class="typing-dot"></span>
              <span class="typing-dot"></span>
            </div>
            <span v-if="!message.isLoading && !message.isTyping"
                  class="message-text"
                  :class="{ 'typewriter': message.showTypewriter }">{{
                      message.showTypewriter ? message.displayText :
                      (message.displayText !== undefined ? message.displayText : message.text)
                  }}</span>
            <span v-if="!message.isLoading && !message.isTyping" class="message-time">{{ message.time }}</span>
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
    <div
      v-if="!isMinimized"
      class="resize-handle resize-sw"
      @mousedown="(event) => startResize('sw', event)"
    ></div>
    <div
      v-if="!isMinimized"
      class="resize-handle resize-w"
      @mousedown="(event) => startResize('w', event)"
    ></div>
    <div
      v-if="!isMinimized"
      class="resize-handle resize-nw"
      @mousedown="(event) => startResize('nw', event)"
    ></div>
    <div
      v-if="!isMinimized"
      class="resize-handle resize-n"
      @mousedown="(event) => startResize('n', event)"
    ></div>
    <div
      v-if="!isMinimized"
      class="resize-handle resize-ne"
      @mousedown="(event) => startResize('ne', event)"
    ></div>
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
            sessionId: null,

            // Typing animation state
            typingTimeouts: [],
            isProcessingResponse: false
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

        // Move popup to body to ensure it appears above Cesium
        if (this.$el && this.$el.parentNode) {
            document.body.appendChild(this.$el)
        }
    },
    beforeDestroy () {
        // Clear typing timeouts
        this.clearTypingTimeouts()

        // Remove event listeners
        document.removeEventListener('mousemove', this.handleMouseMove)
        document.removeEventListener('mouseup', this.handleMouseUp)

        // Remove from body if it was appended there
        if (this.$el && this.$el.parentNode === document.body) {
            document.body.removeChild(this.$el)
        }
    },
    methods: {
        centerPopup () {
            const screenWidth = window.innerWidth
            const screenHeight = window.innerHeight
            // Position popup in bottom right corner with some margin
            this.position.x = Math.max(20, screenWidth - this.size.width - 20)
            this.position.y = Math.max(20, screenHeight - this.size.height - 20)

            console.log('Popup positioned at:', this.position.x, this.position.y)
            console.log('Popup size:', this.size.width, this.size.height)
            console.log('Is visible:', this.isVisible)
        },

        closePopup () {
            this.$emit('close')
        },

        toggleMinimize () {
            this.isMinimized = !this.isMinimized
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

                let newWidth = this.size.width
                let newHeight = this.size.height
                let newX = this.position.x
                let newY = this.position.y

                // Handle horizontal resizing
                if (this.resizeDirection.includes('e')) {
                    newWidth = Math.max(300, Math.min(
                        window.innerWidth - this.position.x,
                        this.initialSize.width + deltaX
                    ))
                }
                if (this.resizeDirection.includes('w')) {
                    const proposedWidth = this.initialSize.width - deltaX
                    const minWidth = 300
                    const maxWidth = this.initialPosition2.x + this.initialSize.width

                    newWidth = Math.max(minWidth, Math.min(maxWidth, proposedWidth))
                    newX = this.initialPosition2.x + this.initialSize.width - newWidth
                }

                // Handle vertical resizing
                if (this.resizeDirection.includes('s')) {
                    newHeight = Math.max(200, Math.min(
                        window.innerHeight - this.position.y,
                        this.initialSize.height + deltaY
                    ))
                }
                if (this.resizeDirection.includes('n')) {
                    const proposedHeight = this.initialSize.height - deltaY
                    const minHeight = 200
                    const maxHeight = this.initialPosition2.y + this.initialSize.height

                    newHeight = Math.max(minHeight, Math.min(maxHeight, proposedHeight))
                    newY = this.initialPosition2.y + this.initialSize.height - newHeight
                }

                // Apply the new dimensions and position
                this.size.width = newWidth
                this.size.height = newHeight
                this.position.x = newX
                this.position.y = newY
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
        },

        addTypingIndicator () {
            // Add typing indicator message
            const typingMessage = {
                type: 'assistant',
                text: '',
                time: '',
                isTyping: true,
                id: 'typing-' + Date.now()
            }

            this.$emit('add-typing-message', typingMessage)

            // Auto-scroll to bottom
            this.$nextTick(() => {
                this.scrollToBottom()
            })
        },

        removeTypingIndicator () {
            this.$emit('remove-typing-message')
        },

        startTypingAnimation (message, finalText) {
            // Clear any existing timeouts
            this.typingTimeouts.forEach(timeout => clearTimeout(timeout))
            this.typingTimeouts = []

            // Set initial state
            message.displayText = ''
            message.showTypewriter = true
            message.isTyping = false

            const words = finalText.split(' ')
            let currentWordIndex = 0

            const typeNextWord = () => {
                if (currentWordIndex < words.length) {
                    if (currentWordIndex === 0) {
                        message.displayText = words[currentWordIndex]
                    } else {
                        message.displayText += ' ' + words[currentWordIndex]
                    }

                    currentWordIndex++

                    // Scroll to bottom as text appears
                    this.$nextTick(() => {
                        this.scrollToBottom()
                    })

                    // Random delay between 50-150ms per word for natural typing
                    const delay = Math.random() * 100 + 50
                    const timeout = setTimeout(typeNextWord, delay)
                    this.typingTimeouts.push(timeout)
                } else {
                    // Typing complete
                    message.displayText = finalText
                    message.showTypewriter = false
                    this.isProcessingResponse = false
                }
            }

            // Start typing after a brief delay
            const initialTimeout = setTimeout(typeNextWord, 300)
            this.typingTimeouts.push(initialTimeout)
        },

        clearTypingTimeouts () {
            this.typingTimeouts.forEach(timeout => clearTimeout(timeout))
            this.typingTimeouts = []
        }
    },
    watch: {
        isVisible (newVal) {
            console.log('ChatbotPopup visibility changed:', newVal)
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
.chatbot-popup {
  position: fixed;
  background: linear-gradient(135deg, rgba(30, 37, 54, 0.95), rgba(19, 83, 136, 0.95));
  border-radius: 12px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.25), 0 4px 12px rgba(0, 0, 0, 0.15);
  overflow: hidden;
  border: 1px solid rgba(255, 255, 255, 0.1);
  display: flex;
  flex-direction: column;
  z-index: 1000000 !important;
  backdrop-filter: blur(10px);
}

.popup-header {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  padding: 12px 16px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  cursor: move;
  user-select: none;
  height: 48px;
  box-sizing: border-box;
  box-shadow: 0 2px 8px rgba(102, 126, 234, 0.2);
}

.popup-title {
  display: flex;
  align-items: center;
  font-weight: 600;
  font-size: 15px;
  letter-spacing: 0.3px;
}

.popup-title i {
  margin-right: 10px;
  font-size: 16px;
}

.popup-controls {
  display: flex;
  gap: 6px;
}

.control-btn {
  background: rgba(255, 255, 255, 0.2);
  border: none;
  color: white;
  width: 28px;
  height: 28px;
  border-radius: 6px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s ease;
  backdrop-filter: blur(8px);
}

.control-btn:hover {
  background: rgba(255, 255, 255, 0.3);
  transform: scale(1.05);
}

.close-btn:hover {
  background: rgba(255, 59, 48, 0.8);
}

.popup-content {
  display: flex;
  flex-direction: column;
  overflow: hidden;
  background: transparent;
}

.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  background: linear-gradient(135deg, rgba(255, 255, 255, 0.08), rgba(255, 255, 255, 0.03));
  min-height: 0;
}

.chat-message {
  display: flex;
  align-items: flex-end;
  margin-bottom: 8px;
  animation: fadeInUp 0.3s ease-out;
}

@keyframes fadeInUp {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.chat-message.user {
  justify-content: flex-end;
}

.chat-message.assistant {
  justify-content: flex-start;
}

.message-bubble {
  max-width: 80%;
  padding: 12px 16px;
  border-radius: 18px;
  position: relative;
  word-wrap: break-word;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
  transition: all 0.2s ease;
}

.message-bubble:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.12);
}

.chat-message.user .message-bubble {
  background: linear-gradient(135deg, #135388, #0f4369);
  color: white;
  border-bottom-right-radius: 6px;
}

.chat-message.assistant .message-bubble {
  background: rgba(255, 255, 255, 0.12);
  color: rgba(255, 255, 255, 0.95);
  border: 1px solid rgba(255, 255, 255, 0.2);
  border-bottom-left-radius: 6px;
}

.loading-message {
  opacity: 0.8;
  animation: pulse 1.5s infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 0.8; }
  50% { opacity: 1; }
}

.loading-spinner {
  display: inline-block;
  margin-right: 8px;
}

.spinner {
  width: 14px;
  height: 14px;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-top: 2px solid rgba(255, 255, 255, 0.8);
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.message-text {
  display: block;
  font-size: 14px;
  line-height: 1.5;
  margin-bottom: 6px;
  white-space: pre-wrap;
  font-weight: 400;
}

.message-time {
  display: block;
  font-size: 11px;
  opacity: 0.6;
  margin-top: 4px;
  text-align: right;
  font-weight: 500;
}

.chat-message.assistant .message-time {
  text-align: left;
}

.chat-input-container {
  display: flex;
  align-items: center;
  padding: 16px 20px;
  background: linear-gradient(135deg, rgba(255, 255, 255, 0.1), rgba(255, 255, 255, 0.05));
  border-top: 1px solid rgba(255, 255, 255, 0.15);
  gap: 12px;
  backdrop-filter: blur(10px);
}

.chat-input {
  flex: 1;
  border: 1px solid rgba(255, 255, 255, 0.2);
  border-radius: 24px;
  padding: 12px 20px;
  background: rgba(255, 255, 255, 0.1);
  color: rgba(255, 255, 255, 0.95);
  font-size: 14px;
  font-weight: 400;
  outline: none;
  transition: all 0.3s ease;
  line-height: 1.4;
}

.chat-input:focus {
  border-color: rgba(255, 255, 255, 0.4);
  background: rgba(255, 255, 255, 0.15);
  box-shadow: 0 0 0 3px rgba(255, 255, 255, 0.1);
  transform: translateY(-1px);
}

.chat-input:disabled {
  background-color: rgba(255, 255, 255, 0.05);
  color: rgba(255, 255, 255, 0.3);
  cursor: not-allowed;
}

.chat-input::placeholder {
  color: rgba(255, 255, 255, 0.6);
  opacity: 0.9;
  font-style: italic;
}

.send-button {
  background: linear-gradient(135deg, #135388, #0f4369);
  color: white;
  border: none;
  border-radius: 50%;
  width: 44px;
  height: 44px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.3s ease;
  outline: none;
  box-shadow: 0 4px 12px rgba(19, 83, 136, 0.3);
  position: relative;
  overflow: hidden;
}

.send-button:not(:disabled):hover {
  background: linear-gradient(135deg, #0f4369, #0a2f4d);
  box-shadow: 0 6px 16px rgba(19, 83, 136, 0.4);
  transform: translateY(-2px) scale(1.05);
}

.send-button:not(:disabled):active {
  transform: translateY(0) scale(0.95);
  box-shadow: 0 2px 8px rgba(19, 83, 136, 0.3);
}

.send-button i {
  font-size: 16px;
  z-index: 1;
  position: relative;
}

.send-button:disabled {
  background: #bdc3c7;
  cursor: not-allowed;
  box-shadow: none;
  transform: none;
}

.send-button:disabled:hover {
  transform: none;
  box-shadow: none;
}

/* Resize handles */
.resize-handle {
  position: absolute;
  background: rgba(102, 126, 234, 0.1);
  border: 1px solid rgba(102, 126, 234, 0.3);
  transition: all 0.2s ease;
  z-index: 10;
}

.resize-handle:hover {
  background: rgba(102, 126, 234, 0.2);
  border-color: rgba(102, 126, 234, 0.5);
  transform: scale(1.1);
}

.resize-handle:active {
  background: rgba(102, 126, 234, 0.3);
  border-color: rgba(102, 126, 234, 0.7);
}

.resize-se {
  bottom: -4px;
  right: -4px;
  width: 12px;
  height: 12px;
  cursor: se-resize;
  border-radius: 0 0 12px 0;
}

.resize-se::after {
  content: '';
  position: absolute;
  bottom: 1px;
  right: 1px;
  width: 8px;
  height: 8px;
  background: linear-gradient(
    -45deg,
    transparent 30%,
    rgba(102, 126, 234, 0.8) 50%,
    transparent 70%
  );
  background-size: 2px 2px;
}

.resize-s {
  bottom: -4px;
  left: 20px;
  right: 20px;
  height: 8px;
  cursor: s-resize;
  border-radius: 0 0 4px 4px;
}

.resize-s::after {
  content: '';
  position: absolute;
  bottom: 1px;
  left: 50%;
  transform: translateX(-50%);
  width: 30px;
  height: 3px;
  background: repeating-linear-gradient(
    90deg,
    transparent,
    transparent 1px,
    rgba(102, 126, 234, 0.8) 1px,
    rgba(102, 126, 234, 0.8) 3px
  );
}

.resize-e {
  top: 56px;
  right: -4px;
  width: 8px;
  bottom: 20px;
  cursor: e-resize;
  border-radius: 0 4px 4px 0;
}

.resize-e::after {
  content: '';
  position: absolute;
  right: 1px;
  top: 50%;
  transform: translateY(-50%);
  width: 3px;
  height: 30px;
  background: repeating-linear-gradient(
    0deg,
    transparent,
    transparent 1px,
    rgba(102, 126, 234, 0.8) 1px,
    rgba(102, 126, 234, 0.8) 3px
  );
}

.resize-sw {
  bottom: -4px;
  left: -4px;
  width: 12px;
  height: 12px;
  cursor: sw-resize;
  border-radius: 0 0 0 12px;
}

.resize-sw::after {
  content: '';
  position: absolute;
  bottom: 1px;
  left: 1px;
  width: 8px;
  height: 8px;
  background: linear-gradient(
    45deg,
    transparent 30%,
    rgba(102, 126, 234, 0.8) 50%,
    transparent 70%
  );
  background-size: 2px 2px;
}

.resize-w {
  top: 56px;
  left: -4px;
  width: 8px;
  bottom: 20px;
  cursor: w-resize;
  border-radius: 4px 0 0 4px;
}

.resize-w::after {
  content: '';
  position: absolute;
  left: 1px;
  top: 50%;
  transform: translateY(-50%);
  width: 3px;
  height: 30px;
  background: repeating-linear-gradient(
    0deg,
    transparent,
    transparent 1px,
    rgba(102, 126, 234, 0.8) 1px,
    rgba(102, 126, 234, 0.8) 3px
  );
}

.resize-nw {
  top: 44px;
  left: -4px;
  width: 12px;
  height: 12px;
  cursor: nw-resize;
  border-radius: 12px 0 0 0;
}

.resize-nw::after {
  content: '';
  position: absolute;
  top: 1px;
  left: 1px;
  width: 8px;
  height: 8px;
  background: linear-gradient(
    135deg,
    transparent 30%,
    rgba(102, 126, 234, 0.8) 50%,
    transparent 70%
  );
  background-size: 2px 2px;
}

.resize-n {
  top: 44px;
  left: 20px;
  right: 20px;
  height: 8px;
  cursor: n-resize;
  border-radius: 4px 4px 0 0;
}

.resize-n::after {
  content: '';
  position: absolute;
  top: 1px;
  left: 50%;
  transform: translateX(-50%);
  width: 30px;
  height: 3px;
  background: repeating-linear-gradient(
    90deg,
    transparent,
    transparent 1px,
    rgba(102, 126, 234, 0.8) 1px,
    rgba(102, 126, 234, 0.8) 3px
  );
}

.resize-ne {
  top: 44px;
  right: -4px;
  width: 12px;
  height: 12px;
  cursor: ne-resize;
  border-radius: 0 12px 0 0;
}

.resize-ne::after {
  content: '';
  position: absolute;
  top: 1px;
  right: 1px;
  width: 8px;
  height: 8px;
  background: linear-gradient(
    -135deg,
    transparent 30%,
    rgba(102, 126, 234, 0.8) 50%,
    transparent 70%
  );
  background-size: 2px 2px;
}

/* Scrollbar styling */
.chat-messages::-webkit-scrollbar {
  width: 8px;
}

.chat-messages::-webkit-scrollbar-track {
  background: rgba(255, 255, 255, 0.1);
  border-radius: 4px;
}

.chat-messages::-webkit-scrollbar-thumb {
  background: rgba(255, 255, 255, 0.3);
  border-radius: 4px;
}

.chat-messages::-webkit-scrollbar-thumb:hover {
  background: rgba(255, 255, 255, 0.5);
}

/* Typing indicator styles */
.typing-message {
  opacity: 0.9;
}

.typing-indicator {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 8px 0;
}

.typing-dot {
  width: 6px;
  height: 6px;
  background: rgba(255, 255, 255, 0.6);
  border-radius: 50%;
  animation: typingBounce 1.4s infinite;
}

.typing-dot:nth-child(2) {
  animation-delay: 0.2s;
}

.typing-dot:nth-child(3) {
  animation-delay: 0.4s;
}

@keyframes typingBounce {
  0%, 60%, 100% {
    transform: translateY(0);
    opacity: 0.4;
  }
  30% {
    transform: translateY(-8px);
    opacity: 1;
  }
}

/* Typewriter effect */
.typewriter {
  position: relative;
}

.typewriter::after {
  content: '|';
  color: rgba(255, 255, 255, 0.7);
  font-weight: 300;
  margin-left: 2px;
  animation: blink 1s infinite;
}

@keyframes blink {
  0%, 50% { opacity: 1; }
  51%, 100% { opacity: 0; }
}
</style>
