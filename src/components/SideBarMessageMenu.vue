<template>
    <div v-if="hasMessages">

        <!--<li v-if="state.plotOn" @click="state.plotOn=!state.plotOn">-->
        <!--<a class="section">-->
        <!--<i class="fas fa-eye-slash fa-lg"></i> Toggle Plot</a>-->
        <!--</li>-->
        <tree-menu
            v-if="Object.keys(availableMessagePresets).length > 0"
            :nodes="availableMessagePresets"
            :label="'Presets'"
            :clean-name="'Presets'"
            :level="0">

        </tree-menu>
        <li v-b-toggle="'messages'">
            <a class="section">
                Plot Individual Field
                <i class="fas fa-caret-down"></i></a>
        </li>

        <b-collapse id="messages">
            <li class="input-li">
                <input id="filterbox" placeholder=" Type here to filter..." v-model="filter">
            </li>
            <template v-for="key of Object.keys(this.messageTypesFiltered).sort()">
                <li class="type" v-bind:key="key">
                    <div
                        v-b-toggle="'type' + key"
                        :title="messageDocs[key.split('[')[0]] ? messageDocs[key.split('[')[0]].doc : ''"
                    >
                        <a class="section">{{key}} <span v-if="messageTypes[key].isArray">{{"[...]"}}</span>
                            <i class="expand fas fa-caret-down"></i></a>
                    </div>
                </li>
                <b-collapse :id="'type' + key" v-bind:key="key+'1'">
                    <template v-for="item in messageTypes[key].complexFields">
                        <li @click="toggle(key, item.name)"
                            class="field"
                            :title="messageDocs[key] ? messageDocs[key][item.name] : ''"
                            v-bind:key="key+'.'+item.name"
                            v-if="isPlottable(key,item.name)
                                && item.name.toLowerCase().indexOf(filter.toLowerCase()) !== -1">
                            <a> {{item.name}}
                                <span v-if="item.units!=='?' && item.units!==''"> ({{item.units}})</span>
                            </a>

                            <a @click="$eventHub.$emit('togglePlot', field.name)" v-if="isPlotted(key,item.name)">
                                <i class="remove-icon fas fa-trash" title="Remove data"></i>
                            </a>
                        </li>
                    </template>
                </b-collapse>
            </template>
        </b-collapse>

        <!-- Chatbot Section -->
        <div class="chatbot-section">
            <li @click="toggleChatbot">
                <a class="section chatbot-toggle">
                    <i class="fas fa-robot"></i>
                    {{ chatbotOpen ? 'Close Chatbot' : 'Open Chatbot' }}
                    <i class="fas fa-caret-down" v-if="!chatbotOpen"></i>
                    <i class="fas fa-caret-up" v-if="chatbotOpen"></i>
                    <button
                        @click.stop="openPopupChatbot"
                        class="popup-button"
                        title="Open in popup window"
                    >
                        <i class="fas fa-external-link-alt"></i>
                    </button>
                </a>
            </li>

            <div
                class="chatbot-container"
                :class="{
                    'chatbot-visible': chatbotOpen,
                    'chatbot-hidden': !chatbotOpen
                }"
            >
                <div v-if="chatbotOpen" class="chat-messages" ref="chatMessages">
                    <div
                        v-for="(message, index) in chatMessages"
                        :key="index"
                        class="chat-message"
                        :class="message.type"
                    >
                        <div class="message-bubble"
                             :class="{ 'loading-message': message.isLoading, 'typing-message': message.isTyping }">
                            <div v-if="message.isTyping" class="typing-indicator">
                                <span class="typing-dot"></span>
                                <span class="typing-dot"></span>
                                <span class="typing-dot"></span>
                            </div>
                            <span v-if="!message.isTyping"
                                  class="message-text"
                                  :class="{ 'typewriter': message.showTypewriter }"
                            >{{
                                message.showTypewriter ? message.displayText :
                                (message.displayText !== undefined ? message.displayText : message.text)
                            }}<span
                                v-if="message.isLoading"
                                class="loading-spinner-inline"
                            ><div class="spinner"></div></span></span>
                            <span v-if="!message.isLoading && !message.isTyping"
                                  class="message-time">{{ message.time }}</span>
                        </div>
                    </div>
                </div>
                <div v-if="chatbotOpen" class="chat-input-container">
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
                <div v-else class="chatbot-placeholder">
                    <i class="fas fa-comment-dots"></i>
                    <span>Chatbot is closed</span>
                </div>
            </div>
        </div>

        <!-- Chatbot Popup -->
        <ChatbotPopup
            :isVisible="showPopupChatbot"
            :chatMessages="popupChatMessages"
            :uploadingFile="uploadingFile"
            @close="closePopupChatbot"
            @send-message="handlePopupMessage"
        />
    </div>
</template>
<script>
import { store } from './Globals.js'
import TreeMenu from './widgets/TreeMenu.vue'
import fastXmlParser from 'fast-xml-parser'
import ChatbotPopup from './ChatbotPopup.vue'

export default {
    name: 'message-menu',
    components: { TreeMenu, ChatbotPopup },
    data () {
        return {
            filter: '',
            checkboxes: {},
            state: store,
            messages: {},
            messageTypes: [],
            hiddenTypes: [
                'MISSION_CURRENT',
                'SYSTEM_TIME', 'HEARTBEAT', 'STATUSTEXT',
                'COMMAND_ACK', 'PARAM_VALUE', 'AUTOPILOT_VERSION',
                'TIMESYNC', 'MISSION_COUNT', 'MISSION_ITEM_INT',
                'MISSION_ITEM', 'MISSION_ITEM_REACHED', 'MISSION_ACK',
                'HOME_POSITION',
                'STRT',
                'ARM',
                'FMT',
                'PARM',
                'MSG',
                'CMD',
                'MODE',
                'ORGN',
                'FMTU',
                'UNIT',
                'MULT'
            ],
            // TODO: lists are nor clear, use objects instead
            messagePresets: {
            },
            userPresets: {},
            messageDocs: {},
            chatbotOpen: false,
            chatMessages: [],
            currentMessage: '',
            sessionId: null,
            flightDataLoaded: false,
            uploadingFile: false,
            uploadingFilename: '',
            showPopupChatbot: false,
            popupChatMessages: [],

            // Typing animation state
            typingTimeouts: [],
            isProcessingResponse: false
        }
    },
    created () {
        this.$eventHub.$on('messageTypes', this.handleMessageTypes)
        this.$eventHub.$on('presetsChanged', this.loadLocalPresets)
        this.$eventHub.$on('flightDataUploadStarted', this.handleFlightDataUploadStarted)
        this.$eventHub.$on('flightDataUploaded', this.handleFlightDataUploaded)
        this.$eventHub.$on('flightDataUploadError', this.handleFlightDataUploadError)
        this.messagePresets = this.loadXmlPresets()
        this.messageDocs = this.loadXmlDocs()
        this.loadLocalPresets()
    },
    beforeDestroy () {
        // Clear typing timeouts
        this.clearTypingTimeouts()

        this.$eventHub.$off('messageTypes')
        this.$eventHub.$off('presetsChanged')
        this.$eventHub.$off('flightDataUploadStarted')
        this.$eventHub.$off('flightDataUploaded')
        this.$eventHub.$off('flightDataUploadError')
    },
    methods: {
        loadXmlPresets () {
            // eslint-disable-next-line
            const graphs = {}
            const files = [
                require('../assets/mavgraphs.xml'),
                require('../assets/mavgraphs2.xml'),
                require('../assets/ekfGraphs.xml'),
                require('../assets/ekf3Graphs.xml')
            ]
            for (const contents of files) {
                const result = fastXmlParser.parse(contents.default, { ignoreAttributes: false })
                const igraphs = result.graphs
                for (const graph of igraphs.graph) {
                    let i = ''
                    const name = graph['@_name']
                    if (!Array.isArray(graph.expression)) {
                        graph.expression = [graph.expression]
                    }
                    for (const expression of graph.expression) {
                        const fields = []
                        for (let exp of expression.split(' ')) {
                            if (exp.indexOf(':') >= 0) {
                                exp = exp.replace(':2', '')
                                fields.push([exp, 1])
                            } else {
                                fields.push([exp, 0])
                            }
                        }
                        graphs[name + i] = fields
                        // workaround to avoid replacing a key
                        // TODO: implement this in a way that doesn't need this hack
                        i += ' '
                    }
                }
            }
            return graphs
        },
        loadLocalPresets () {
            const saved = window.localStorage.getItem('savedFields')
            if (saved !== null) {
                this.userPresets = JSON.parse(saved)
                for (const preset in this.userPresets) {
                    for (const message in this.userPresets[preset]) {
                        // Field 3 means it is a user preset and can be deleted
                        this.userPresets[preset][message][3] = 1
                    }
                }
            }
        },
        loadXmlDocs () {
            const logDocs = {}
            const files = [
                require('../assets/logmetadata/plane.xml'),
                require('../assets/logmetadata/copter.xml'),
                require('../assets/logmetadata/tracker.xml'),
                require('../assets/logmetadata/rover.xml')
            ]
            for (const contents of files) {
                const result = fastXmlParser.parse(contents.default, { ignoreAttributes: false })
                const igraphs = result.loggermessagefile
                for (const graph of igraphs.logformat) {
                    logDocs[graph['@_name']] = { doc: graph.description }
                    for (const field of graph.fields.field) {
                        logDocs[graph['@_name']][field['@_name']] = field.description
                    }
                }
            }
            return logDocs
        },
        handleMessageTypes (messageTypes) {
            if (this.$route.query.plots) {
                this.state.plotOn = true
            }
            const newMessages = {}
            // populate list of message types
            for (const messageType of Object.keys(messageTypes)) {
                if (messageTypes[messageType].instances !== undefined) {
                    continue
                }
                this.$set(this.checkboxes, messageType, messageTypes[messageType].expressions.expressions)
                newMessages[messageType] = messageTypes[messageType]
            }
            // populate checkbox status
            for (const messageType of Object.keys(messageTypes)) {
                if (messageTypes[messageType].instances !== undefined) {
                    continue
                }
                this.checkboxes[messageType] = { expressions: {} }
                // for (let field of this.getMessageNumericField(this.state.messages[messageType][0])) {
                for (const field of messageTypes[messageType].expressions) {
                    if (this.state.plotOn) {
                        this.checkboxes[messageType].expressions[field] =
                            this.$route.query?.plots?.indexOf(messageType + '.' + field) !== -1
                    } else {
                        this.checkboxes[messageType].expressions[field] = false
                    }
                }
            }
            this.messageTypes = newMessages
            this.$set(this.state, 'messageTypes', newMessages)
        },
        isPlotted (message, field) {
            const fullname = message + '.' + field
            for (const field of this.state.expressions) {
                if (field.name === fullname) {
                    return true
                }
            }
            return false
        },
        getMessageNumericField (message) {
            const numberFields = []
            if (message && message.fieldnames) {
                for (const field of message.fieldnames) {
                    if (!isNaN(message[field])) {
                        numberFields.push(field)
                    }
                }
            }
            return numberFields
        },
        toggle (message, item) {
            this.state.plotOn = true
            this.$nextTick(function () {
                this.$eventHub.$emit('togglePlot', message + '.' + item)
            })
        },
        isPlottable (msgtype, item) {
            return item !== 'TimeUS'
        },
        collapse (name) {
            if (document.getElementById(name) &&
                document.getElementById(name).style &&
                document.getElementById(name).style.display !== 'none') {
                this.$root.$emit('bv::toggle::collapse', name)
            }
        },
        expand (name) {
            if (document.getElementById(name) &&
                document.getElementById(name).style &&
                document.getElementById(name).style.display === 'none') {
                this.$root.$emit('bv::toggle::collapse', name)
            }
        },
        findMessagesInExpression (expression) {
            // delete all expressions after dots (and dots)
            const toDelete = /\.[A-Za-z-0-9_]+/g
            const name = expression.replace(toDelete, '')
            const RE = /[A-Z][A-Z0-9_]+(\[0-9\])?/g
            const fields = name.match(RE)
            if (fields === null) {
                return []
            }
            return fields
        },
        isAvailable (msg) {
            const msgRe = /[A-Z][A-Z0-9_]+(\[[0-9]\])?(\.[a-zA-Z0-9_]+)?/g
            const match = msg[0].match(msgRe)
            if (!match) {
                return true
            }
            const msgName = match[0].split('.')[0]
            if (!this.messageTypes[msgName]) {
                return false
            }
            const fieldName = match[0].split('.')[1]
            if (fieldName === undefined) {
                return true
            }
            if (!this.messageTypes[msgName].complexFields[fieldName]) {
                console.log('missing field ' + msgName + '.' + fieldName)
                return false
            }
            return true
        },
        toggleChatbot () {
            this.chatbotOpen = !this.chatbotOpen
            if (this.chatbotOpen && this.chatMessages.length === 0) {
                // Add welcome message when opening chatbot for the first time
                this.chatMessages.push({
                    type: 'bot',
                    text: 'Hello! I can help you analyze your UAV flight data. ' +
                          'Upload a .bin flight log file above, then ask me questions like: ' +
                          '"What was the maximum altitude?", "Were there any GPS issues?", ' +
                          'or "How long was the flight?" I can also answer general UAV questions.',
                    time: this.getCurrentTime()
                })
            }
            // Focus on input when chatbot opens
            if (this.chatbotOpen) {
                this.$nextTick(() => {
                    if (this.$refs.chatInput) {
                        this.$refs.chatInput.focus()
                    }
                })
            }
        },
        sendMessage () {
            if (this.currentMessage.trim() === '') {
                return
            }

            // Add user message
            this.chatMessages.push({
                type: 'user',
                text: this.currentMessage.trim(),
                time: this.getCurrentTime()
            })

            const userMessage = this.currentMessage.trim()
            this.currentMessage = ''

            // Scroll to bottom
            this.$nextTick(() => {
                this.scrollToBottom()
            })

            // Call backend API
            this.callChatbotAPI(userMessage)
        },
        async callChatbotAPI (message) {
            try {
                if (!this.sessionId) {
                    this.sessionId = 'session_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9)
                }

                // Add typing indicator
                this.addTypingIndicator(false)

                const response = await fetch('http://localhost:8001/chat', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        content: message,
                        sessionId: this.sessionId,
                        timestamp: new Date().toISOString()
                    })
                })

                if (!response.ok) {
                    const errorText = await response.text()
                    console.error('Chat API failed:', response.status, errorText)
                    throw new Error(`HTTP error! status: ${response.status}`)
                }

                const data = await response.json()

                // Remove typing indicator
                this.removeTypingIndicator(false)

                // Add bot response with typing animation
                const botMessage = {
                    type: 'bot',
                    text: data.content || 'Sorry, I could not process your request.',
                    time: this.getCurrentTime(),
                    displayText: '',
                    showTypewriter: false,
                    _originalText: data.content || 'Sorry, I could not process your request.'
                }
                this.chatMessages.push(botMessage)

                // Start typing animation immediately
                this.startTypingAnimation(botMessage, botMessage._originalText)

                if (data.suggested_questions && data.suggested_questions.length > 0) {
                    // Add suggested questions after typing is complete
                    setTimeout(() => {
                        const suggestionMessage = {
                            type: 'bot',
                            text: 'You might also want to ask: ' +
                                  data.suggested_questions.join(', '),
                            time: this.getCurrentTime(),
                            displayText: '',
                            showTypewriter: false,
                            _originalText: 'You might also want to ask: ' +
                                          data.suggested_questions.join(', ')
                        }
                        this.chatMessages.push(suggestionMessage)
                        this.startTypingAnimation(suggestionMessage, suggestionMessage._originalText)
                    }, 2000)
                }
            } catch (error) {
                console.error('Error calling chatbot API:', error)

                // Remove typing indicator
                this.removeTypingIndicator(false)

                const errorMessage = {
                    type: 'bot',
                    text: 'Sorry, there was an error processing your request. Please try again.',
                    time: this.getCurrentTime(),
                    displayText: '',
                    showTypewriter: false,
                    _originalText: 'Sorry, there was an error processing your request. Please try again.'
                }
                this.chatMessages.push(errorMessage)
                this.startTypingAnimation(errorMessage, errorMessage._originalText)
            }

            this.$nextTick(() => {
                this.scrollToBottom()
            })
        },
        getCurrentTime () {
            const now = new Date()
            return now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
        },
        scrollToBottom () {
            if (this.$refs.chatMessages) {
                this.$refs.chatMessages.scrollTop = this.$refs.chatMessages.scrollHeight
            }
        },
        handleFlightDataUploadStarted (event) {
            this.uploadingFile = true
            this.uploadingFilename = event.filename

            // Add loading message to sidebar chat
            this.chatMessages.push({
                type: 'bot',
                text: 'Analyzing flight log data...',
                time: this.getCurrentTime(),
                isLoading: true
            })

            // Also add loading message to popup chat if it has messages
            if (this.popupChatMessages.length > 0) {
                this.popupChatMessages.push({
                    type: 'assistant',
                    text: 'Analyzing flight log data...',
                    time: this.getCurrentTime(),
                    isLoading: true
                })
            }

            if (this.chatbotOpen) {
                this.$nextTick(() => {
                    this.scrollToBottom()
                })
            }
        },
        handleFlightDataUploaded (event) {
            this.uploadingFile = false
            this.uploadingFilename = ''
            this.flightDataLoaded = true

            const successMessageText = `Flight log analysis complete! "${event.filename}" ` +
                                     'has been successfully processed. ' +
                                     'Feel free to ask me questions about this flight data!'

            // Remove any existing loading messages from sidebar chat
            this.chatMessages = this.chatMessages.filter(msg => !msg.isLoading)

            // Add success message with typing animation setup
            const botMessage = {
                type: 'bot',
                text: successMessageText,
                time: this.getCurrentTime(),
                displayText: '',
                showTypewriter: false,
                _originalText: successMessageText
            }
            this.chatMessages.push(botMessage)

            // Start typing animation for sidebar
            this.startTypingAnimation(botMessage, botMessage._originalText)

            // Also update popup chat messages
            if (this.popupChatMessages.length > 0) {
                // Remove any existing loading messages from popup chat
                this.popupChatMessages = this.popupChatMessages.filter(msg => !msg.isLoading)

                // Add success message to popup chat with typing animation setup
                const popupMessage = {
                    type: 'assistant',
                    text: successMessageText,
                    time: this.getCurrentTime(),
                    displayText: '',
                    showTypewriter: false,
                    _originalText: successMessageText
                }
                this.popupChatMessages.push(popupMessage)

                // Start typing animation for popup (if popup component exists)
                this.$nextTick(() => {
                    const popupComponent = this.$children.find(child => child.$options.name === 'ChatbotPopup')
                    if (popupComponent) {
                        popupComponent.startTypingAnimation(popupMessage, popupMessage._originalText)
                    }
                })
            }

            if (this.chatbotOpen) {
                this.$nextTick(() => {
                    this.scrollToBottom()
                })
            }
        },
        handleFlightDataUploadError (event) {
            this.uploadingFile = false
            this.uploadingFilename = ''

            const errorMessage = {
                type: 'bot',
                text: `Error analyzing flight log "${event.filename}": ${event.error}. ` +
                      'Please try uploading the file again.',
                time: this.getCurrentTime()
            }

            // Remove any existing loading messages from sidebar chat
            this.chatMessages = this.chatMessages.filter(msg => !msg.isLoading)
            this.chatMessages.push(errorMessage)

            // Also update popup chat messages
            if (this.popupChatMessages.length > 0) {
                // Remove any existing loading messages from popup chat
                this.popupChatMessages = this.popupChatMessages.filter(msg => !msg.isLoading)

                // Add error message to popup chat with correct type
                this.popupChatMessages.push({
                    type: 'assistant',
                    text: `Error analyzing flight log "${event.filename}": ${event.error}. ` +
                          'Please try uploading the file again.',
                    time: this.getCurrentTime()
                })
            }

            if (this.chatbotOpen) {
                this.$nextTick(() => {
                    this.scrollToBottom()
                })
            }
        },
        openPopupChatbot () {
            // Copy current messages to popup, or add welcome message if empty
            if (this.chatMessages.length > 0) {
                // Convert 'bot' type to 'assistant' type for popup
                this.popupChatMessages = this.chatMessages.map(msg => ({
                    ...msg,
                    type: msg.type === 'bot' ? 'assistant' : msg.type
                }))
            } else {
                this.popupChatMessages = [{
                    type: 'assistant',
                    text: 'Hello! I can help you analyze your UAV flight data. ' +
                          'Upload a .bin flight log file in the main area, then ask me questions like: ' +
                          '"What was the maximum altitude?", "Were there any GPS issues?", ' +
                          'or "How long was the flight?" I can also answer general UAV questions.',
                    time: this.getCurrentTime()
                }]
            }
            this.showPopupChatbot = true
        },
        closePopupChatbot () {
            this.showPopupChatbot = false
        },
        handlePopupMessage (messageData) {
            // Add user message to popup messages
            this.addMessageToPopup(messageData.text, 'user')

            // Send the message to backend
            this.sendMessageToBackend(messageData.text, messageData.sessionId)
        },
        addMessageToPopup (text, type, isLoading = false) {
            const message = {
                text: text,
                type: type,
                time: new Date().toLocaleTimeString(),
                isLoading: isLoading
            }
            this.popupChatMessages.push(message)
        },
        async sendMessageToBackend (message, sessionId) {
            try {
                // Add typing indicator to popup
                this.addTypingIndicator(true)

                const payload = {
                    content: message,
                    sessionId: sessionId,
                    timestamp: new Date().toISOString()
                }

                const response = await fetch('http://localhost:8001/chat', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify(payload)
                })

                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`)
                }

                const data = await response.json()

                // Remove typing indicator
                this.removeTypingIndicator(true)

                // Add bot response with typing animation
                const botMessage = {
                    text: data.content || 'Sorry, I could not process your request.',
                    type: 'assistant',
                    time: new Date().toLocaleTimeString(),
                    displayText: '',
                    showTypewriter: false,
                    _originalText: data.content || 'Sorry, I could not process your request.'
                }
                this.popupChatMessages.push(botMessage)

                // Start typing animation using ChatbotPopup's method
                this.$children.find(child => child.$options.name === 'ChatbotPopup')
                    ?.startTypingAnimation(botMessage, botMessage._originalText)

                if (data.suggested_questions && data.suggested_questions.length > 0) {
                    setTimeout(() => {
                        const suggestionMessage = {
                            text: 'You might also want to ask: ' +
                                  data.suggested_questions.join(', '),
                            type: 'assistant',
                            time: new Date().toLocaleTimeString(),
                            displayText: '',
                            showTypewriter: false,
                            _originalText: 'You might also want to ask: ' +
                                          data.suggested_questions.join(', ')
                        }
                        this.popupChatMessages.push(suggestionMessage)
                        this.$children.find(child => child.$options.name === 'ChatbotPopup')
                            ?.startTypingAnimation(suggestionMessage, suggestionMessage._originalText)
                    }, 2000)
                }
            } catch (error) {
                console.error('Error sending message to backend:', error)

                // Remove typing indicator
                this.removeTypingIndicator(true)

                const errorMessage = {
                    text: 'Sorry, there was an error processing your request. Please try again.',
                    type: 'assistant',
                    time: new Date().toLocaleTimeString(),
                    displayText: '',
                    showTypewriter: false
                }
                this.popupChatMessages.push(errorMessage)
                this.$children.find(child => child.$options.name === 'ChatbotPopup')
                    ?.startTypingAnimation(errorMessage, errorMessage.text)
            }
        },
        addTypingIndicator (isPopup = false) {
            const messageArray = isPopup ? this.popupChatMessages : this.chatMessages

            // Add typing indicator message
            const typingMessage = {
                type: isPopup ? 'assistant' : 'bot',
                text: '',
                time: '',
                isTyping: true,
                id: 'typing-' + Date.now()
            }

            messageArray.push(typingMessage)

            // Auto-scroll to bottom
            this.$nextTick(() => {
                this.scrollToBottom()
            })
        },
        removeTypingIndicator (isPopup = false) {
            const messageArray = isPopup ? this.popupChatMessages : this.chatMessages
            const typingIndex = messageArray.findIndex(msg => msg.isTyping)
            if (typingIndex !== -1) {
                messageArray.splice(typingIndex, 1)
            }
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
    computed: {
        hasMessages () {
            return Object.keys(this.messageTypes).length > 0
        },
        messageTypesFiltered () {
            const filtered = {}
            for (const key of Object.keys(this.messageTypes)) {
                if (this.hiddenTypes.indexOf(key) === -1) {
                    if (this.filter === '') {
                        this.collapse('type' + key)
                        filtered[key] = this.messageTypes[key]
                        continue
                    }
                    if (this.messageTypes[key].expressions
                        .filter(field => field.toLowerCase().indexOf(this.filter.toLowerCase()) !== -1)
                        .length > 0) {
                        filtered[key] = this.messageTypes[key]
                        // console.log('type' + key, document.getElementById('type' + key))
                        this.expand('type' + key)
                    } else {
                        this.collapse('type' + key)
                    }
                }
            }
            return filtered
        },
        availableMessagePresets () {
            const dict = {}
            // do it for default messages
            for (const [key, value] of Object.entries(this.messagePresets)) {
                let missing = false
                let color = 0
                for (const field of value) {
                    // If all of the expressions match, add this and move on
                    if (field[0] === '') {
                        continue
                    }
                    missing = missing || !this.isAvailable(field)
                    if (!missing) {
                        if (!(key in dict)) {
                            dict[key] = { messages: [[...field, color++]] }
                        } else {
                            dict[key].messages.push([...field, color++])
                        }
                    }
                }
                if (missing) {
                    delete dict[key]
                }
            }
            // And again for user presets
            for (const [key, value] of Object.entries(this.userPresets)) {
                let missing = false
                let color = 0
                for (const field of value) {
                    // If all of the expressions match, add this and move on
                    missing = missing || !this.isAvailable(field)
                    if (!missing) {
                        if (!(key in dict)) {
                            dict[key] = { messages: [[...field, color++]] }
                        } else {
                            dict[key].messages.push([...field, color++])
                        }
                    }
                }
            }
            const newDict = {}
            for (const [key, value] of Object.entries(dict)) {
                let current = newDict
                const fields = key.trim().split('/')
                const lastField = fields.pop()
                for (const field of fields) {
                    if (!(field in current)) {
                        console.log('overwriting ' + field)
                        current[field] = {}
                    }
                    current = current[field]
                }
                current[lastField] = value
            }
            return newDict
        }
    }
}
</script>
<style scoped>
    i {
        margin: 5px;
    }
    i.expand {
        float: right;
    }
    li > div {
        display: inline-block;
        width: 100%;
    }
    li.field {
        line-height: 29px;
        padding-left: 40px;
        font-size: 90%;
        display: inline-block;
        vertical-align: middle;
        width: 100%;
    }
    li.type {
        line-height: 30px;
        padding-left: 10px;
        font-size: 85%;
    }
    input {
        margin: 12px 12px 15px 10px;
        border: 2px solid #ccc;
        -webkit-border-radius: 4px;
        -moz-border-radius: 4px;
        border-radius: 4px;
        background-color: rgba(255, 255, 255, 0.897);
        color: rgb(51, 51, 51);
        width: 92%;
    }
    input:focus {
        outline: none;
        border: 2px solid #135388;
    }
    .input-li:hover {
        background-color: rgba(30, 37, 54, 0.205);
        border-left: 3px solid rgba(24, 30, 44, 0.212);
    }
    ::placeholder { /* Chrome, Firefox, Opera, Safari 10.1+ */
        color: rgb(148, 147, 147);
        opacity: 1; /* Firefox */
    }
    :-ms-input-placeholder { /* Internet Explorer 10-11 */
        color: #2e2e2e;
    }
    ::-ms-input-placeholder { /* Microsoft Edge */
        color: #2e2e2e;
    }
    i.remove-icon {
        float: right;
    }

    /* Chatbot Styles */
    .chatbot-toggle {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 12px;
        padding: 14px 18px;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border-radius: 12px;
        margin: 12px 8px;
        transition: all 0.4s cubic-bezier(0.25, 0.46, 0.45, 0.94);
        box-shadow:
            0 6px 24px rgba(102, 126, 234, 0.25),
            0 2px 6px rgba(0, 0, 0, 0.08);
        position: relative;
        overflow: hidden;
        cursor: pointer;
        border: 1px solid rgba(255, 255, 255, 0.2);
        backdrop-filter: blur(10px);
        font-weight: 600;
        font-size: 14px;
        letter-spacing: 0.3px;
    }

    .chatbot-toggle::before {
        content: '';
        position: absolute;
        top: 0;
        left: -100%;
        width: 100%;
        height: 100%;
        background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.2), transparent);
        transition: left 0.5s ease;
    }

    .chatbot-toggle:hover::before {
        left: 100%;
    }

    .chatbot-toggle:hover {
        background: linear-gradient(135deg, #764ba2 0%, #667eea 100%);
        box-shadow:
            0 8px 32px rgba(102, 126, 234, 0.35),
            0 4px 16px rgba(0, 0, 0, 0.12);
        transform: translateY(-3px) scale(1.02);
        border-color: rgba(255, 255, 255, 0.35);
    }

    .chatbot-toggle:active {
        transform: translateY(-1px) scale(1.005);
        box-shadow:
            0 4px 16px rgba(102, 126, 234, 0.3),
            0 2px 6px rgba(0, 0, 0, 0.1);
    }

    .chatbot-toggle i {
        font-size: 17px;
        filter: drop-shadow(0 1px 3px rgba(0, 0, 0, 0.2));
        transition: transform 0.3s ease;
    }

    .chatbot-toggle:hover i {
        transform: scale(1.1);
    }

    .popup-button {
        background: linear-gradient(135deg, rgba(255, 255, 255, 0.3), rgba(255, 255, 255, 0.15));
        border: 1px solid rgba(255, 255, 255, 0.4);
        color: white;
        width: 34px;
        height: 34px;
        border-radius: 8px;
        cursor: pointer;
        display: flex;
        align-items: center;
        justify-content: center;
        transition: all 0.3s cubic-bezier(0.25, 0.46, 0.45, 0.94);
        flex-shrink: 0;
        backdrop-filter: blur(8px);
        box-shadow:
            0 3px 8px rgba(0, 0, 0, 0.12),
            inset 0 1px 0 rgba(255, 255, 255, 0.3);
        position: relative;
        overflow: hidden;
    }

    .popup-button::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background: linear-gradient(135deg, rgba(255, 255, 255, 0.2), rgba(255, 255, 255, 0.05));
        opacity: 0;
        transition: opacity 0.3s ease;
    }

    .popup-button:hover::before {
        opacity: 1;
    }

    .popup-button:hover {
        background: linear-gradient(135deg, rgba(255, 255, 255, 0.5), rgba(255, 255, 255, 0.3));
        transform: translateY(-2px) scale(1.08);
        box-shadow:
            0 5px 14px rgba(0, 0, 0, 0.2),
            inset 0 1px 0 rgba(255, 255, 255, 0.5);
        border-color: rgba(255, 255, 255, 0.7);
    }

    .popup-button:active {
        transform: translateY(0) scale(1.03);
        box-shadow:
            0 2px 6px rgba(0, 0, 0, 0.12),
            inset 0 1px 0 rgba(255, 255, 255, 0.25);
    }

    .popup-button i {
        font-size: 14px;
        filter: drop-shadow(0 1px 2px rgba(0, 0, 0, 0.25));
        transition: transform 0.2s ease;
        opacity: 0.95;
        margin-right: -1px;
    }

    .popup-button:hover i {
        transform: scale(1.15);
        opacity: 1;
    }

    .chatbot-section {
        display: flex;
        flex-direction: column;
        margin: 8px 0;
    }

    .chatbot-container {
        background: linear-gradient(135deg, rgba(30, 37, 54, 0.95), rgba(19, 83, 136, 0.95));
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 12px;
        margin: 8px 12px;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.25), 0 4px 12px rgba(0, 0, 0, 0.15);
        overflow: hidden;
        backdrop-filter: blur(10px);
        display: flex;
        flex-direction: column;
        height: 390px; /* Fixed height to prevent sidebar resizing */
        min-height: 390px;
        max-height: 390px;
        transition: all 0.4s cubic-bezier(0.25, 0.46, 0.45, 0.94);
    }

    .chatbot-container.chatbot-visible {
        opacity: 1;
        transform: translateY(0) scale(1);
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.25), 0 4px 12px rgba(0, 0, 0, 0.15);
    }

    .chatbot-container.chatbot-hidden {
        opacity: 0.7;
        transform: translateY(-8px) scale(0.98);
        box-shadow: 0 4px 16px rgba(0, 0, 0, 0.15);
    }

    .chatbot-placeholder {
        display: none;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        height: 100%;
        color: rgba(255, 255, 255, 0.4);
        font-style: italic;
        gap: 12px;
        background: transparent;
        border-radius: 12px;
        margin: 1px;
    }

    .chatbot-placeholder i {
        font-size: 36px;
        opacity: 0.25;
        color: rgba(255, 255, 255, 0.3);
        animation: float 3s ease-in-out infinite;
    }

    @keyframes float {
        0%, 100% { transform: translateY(0px); }
        50% { transform: translateY(-6px); }
    }

    .chatbot-placeholder span {
        font-size: 15px;
        opacity: 0.6;
        font-weight: 500;
        letter-spacing: 0.3px;
        color: rgba(255, 255, 255, 0.6);
    }

    .chat-messages {
        height: 300px;
        min-height: 300px;
        max-height: 300px;
        overflow-y: auto;
        padding: 18px;
        display: flex;
        flex-direction: column;
        gap: 12px;
        background: linear-gradient(135deg, rgba(255, 255, 255, 0.08), rgba(255, 255, 255, 0.03));
        border-radius: 12px 12px 0 0;
        flex: 1;
    }

    .chat-message {
        display: flex;
        align-items: flex-end;
        margin-bottom: 10px;
        animation: messageSlideIn 0.3s ease-out;
    }

    @keyframes messageSlideIn {
        from {
            opacity: 0;
            transform: translateY(15px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }

    .chat-message.user {
        justify-content: flex-end;
    }

    .chat-message.bot {
        justify-content: flex-start;
    }

    .message-bubble {
        max-width: 82%;
        padding: 12px 16px;
        border-radius: 18px;
        position: relative;
        word-wrap: break-word;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
        transition: all 0.2s ease;
    }

    .loading-message .message-bubble {
        padding: 12px 32px 12px 16px;
        max-width: 78%;
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

    .chat-message.bot .message-bubble {
        background: rgba(255, 255, 255, 0.12);
        color: rgba(255, 255, 255, 0.95);
        border: 1px solid rgba(255, 255, 255, 0.2);
        border-bottom-left-radius: 6px;
    }

    .message-text {
        display: block;
        font-size: 14px;
        line-height: 1.5;
        font-weight: 400;
        margin-bottom: 6px;
        white-space: pre-wrap;
    }

    .loading-message .message-text {
        white-space: nowrap;
        margin-bottom: 0;
        display: inline-flex;
        align-items: center;
    }

    .message-time {
        display: block;
        font-size: 11px;
        opacity: 0.6;
        margin-top: 4px;
        text-align: right;
        font-weight: 500;
    }

    .chat-message.bot .message-time {
        text-align: left;
    }

    .chat-input-container {
        display: flex;
        align-items: center;
        padding: 16px 16px 16px 16px;
        background: linear-gradient(135deg, rgba(255, 255, 255, 0.12), rgba(255, 255, 255, 0.08));
        border-radius: 0 0 12px 12px;
        border-top: 1px solid rgba(255, 255, 255, 0.15);
        gap: 10px;
        backdrop-filter: blur(15px);
        box-shadow: 0 -2px 8px rgba(0, 0, 0, 0.1);
    }

    .chat-input {
        flex: 1;
        border: 1px solid rgba(255, 255, 255, 0.25);
        border-radius: 24px;
        padding: 12px 18px;
        background: rgba(255, 255, 255, 0.12);
        color: rgba(255, 255, 255, 0.95);
        font-size: 13px;
        font-weight: 400;
        outline: none;
        transition: all 0.3s cubic-bezier(0.25, 0.46, 0.45, 0.94);
        line-height: 1.4;
        box-shadow:
            0 2px 8px rgba(0, 0, 0, 0.08),
            inset 0 1px 0 rgba(255, 255, 255, 0.1);
        backdrop-filter: blur(10px);
        min-width: 0;
    }

    .chat-input:focus {
        border-color: rgba(255, 255, 255, 0.5);
        background: rgba(255, 255, 255, 0.18);
        box-shadow:
            0 0 0 2px rgba(255, 255, 255, 0.15),
            0 4px 16px rgba(0, 0, 0, 0.12),
            inset 0 1px 0 rgba(255, 255, 255, 0.2);
        transform: translateY(-1px);
        color: rgba(255, 255, 255, 1);
    }

    .chat-input:hover:not(:disabled) {
        border-color: rgba(255, 255, 255, 0.35);
        background: rgba(255, 255, 255, 0.15);
        box-shadow:
            0 3px 12px rgba(0, 0, 0, 0.1),
            inset 0 1px 0 rgba(255, 255, 255, 0.15);
    }

    .chat-input:disabled {
        background-color: rgba(255, 255, 255, 0.05);
        color: rgba(255, 255, 255, 0.4);
        cursor: not-allowed;
        border-color: rgba(255, 255, 255, 0.1);
        transform: none;
        box-shadow: none;
    }

    .chat-input::placeholder {
        color: rgba(255, 255, 255, 0.65);
        opacity: 1;
        font-style: italic;
        font-weight: 300;
    }

    .send-button {
        background: linear-gradient(135deg, #4a90e2 0%, #357abd 50%, #1e5a8a 100%);
        color: white;
        border: none;
        border-radius: 50%;
        width: 42px;
        height: 42px;
        cursor: pointer;
        display: flex;
        align-items: center;
        justify-content: center;
        transition: all 0.3s cubic-bezier(0.25, 0.46, 0.45, 0.94);
        outline: none;
        box-shadow:
            0 3px 12px rgba(74, 144, 226, 0.4),
            0 1px 3px rgba(0, 0, 0, 0.1),
            inset 0 1px 0 rgba(255, 255, 255, 0.2);
        position: relative;
        overflow: hidden;
        flex-shrink: 0;
        border: 1px solid rgba(255, 255, 255, 0.2);
    }

    .send-button::before {
        content: '';
        position: absolute;
        top: 0;
        left: -100%;
        width: 100%;
        height: 100%;
        background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.3), transparent);
        transition: left 0.5s ease;
    }

    .send-button:not(:disabled):hover::before {
        left: 100%;
    }

    .send-button:not(:disabled):hover {
        background: linear-gradient(135deg, #357abd 0%, #2a6ba8 50%, #1e5a8a 100%);
        box-shadow:
            0 5px 18px rgba(74, 144, 226, 0.5),
            0 3px 6px rgba(0, 0, 0, 0.15),
            inset 0 1px 0 rgba(255, 255, 255, 0.3);
        transform: translateY(-2px) scale(1.05);
        border-color: rgba(255, 255, 255, 0.4);
    }

    .send-button:not(:disabled):active {
        transform: translateY(-1px) scale(1.02);
        box-shadow:
            0 2px 8px rgba(74, 144, 226, 0.4),
            0 1px 3px rgba(0, 0, 0, 0.1),
            inset 0 1px 0 rgba(255, 255, 255, 0.2);
    }

    .send-button i {
        font-size: 15px;
        z-index: 1;
        position: relative;
        filter: drop-shadow(0 1px 2px rgba(0, 0, 0, 0.3));
        transition: transform 0.2s ease;
    }

    .send-button:not(:disabled):hover i {
        transform: scale(1.1) translateX(1px);
    }

    .send-button:disabled {
        background: linear-gradient(135deg, #6c757d, #5a6268);
        cursor: not-allowed;
        box-shadow:
            0 2px 8px rgba(0, 0, 0, 0.1),
            inset 0 1px 0 rgba(255, 255, 255, 0.1);
        transform: none;
        border-color: rgba(255, 255, 255, 0.1);
        opacity: 0.6;
    }

    .send-button:disabled:hover {
        transform: none;
        box-shadow:
            0 2px 8px rgba(0, 0, 0, 0.1),
            inset 0 1px 0 rgba(255, 255, 255, 0.1);
    }

    .send-button:disabled i {
        filter: none;
        opacity: 0.7;
    }

    /* Scrollbar styling for chat messages */
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

    @media (min-width: 575px) and (max-width: 992px) {
       a {
        padding: 2px 60px 2px 55px !important;
       }
    }

    @media (max-width: 400px) {
        .chat-input-container {
            padding: 10px 12px;
            gap: 8px;
        }

        .chat-input {
            padding: 10px 15px;
            font-size: 13px;
        }

        .send-button {
            width: 38px;
            height: 38px;
        }

        .send-button i {
            font-size: 14px;
        }
    }

    /* Loading States */
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

    .loading-spinner-inline {
        display: inline-flex;
        align-items: center;
        margin-left: 6px;
        margin-right: 4px;
    }

    .loading-spinner-inline .spinner {
        width: 10px;
        height: 10px;
        border: 1px solid rgba(255, 255, 255, 0.3);
        border-top: 1px solid rgba(255, 255, 255, 0.8);
        border-radius: 50%;
        animation: spin 1s linear infinite;
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
