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
                        <div class="message-bubble" :class="{ 'loading-message': message.isLoading }">
                            <div v-if="message.isLoading" class="loading-spinner">
                                <div class="spinner"></div>
                            </div>
                            <span class="message-text">{{ message.text }}</span>
                            <span class="message-time">{{ message.time }}</span>
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
            popupChatMessages: []
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
                text: this.currentMessage,
                time: this.getCurrentTime()
            })

            const userMessage = this.currentMessage
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

                this.chatMessages.push({
                    type: 'bot',
                    text: data.content || 'Sorry, I could not process your request.',
                    time: this.getCurrentTime()
                })

                if (data.suggested_questions && data.suggested_questions.length > 0) {
                    this.chatMessages.push({
                        type: 'bot',
                        text: 'You might also want to ask: ' + data.suggested_questions.join(', '),
                        time: this.getCurrentTime()
                    })
                }
            } catch (error) {
                console.error('Error calling chatbot API:', error)

                this.chatMessages.push({
                    type: 'bot',
                    text: `❌ Error analyzing flight log "${event.filename}": ${event.error}. ` +
                          'Please try uploading the file again.',
                    time: this.getCurrentTime()
                })
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

            // Add loading message to chat
            this.chatMessages.push({
                type: 'bot',
                text: `📡 Analyzing flight log "${event.filename}"... ` +
                      'This may take a moment while I parse the flight data and detect any anomalies.',
                time: this.getCurrentTime(),
                isLoading: true
            })

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

            // Remove any existing loading messages
            this.chatMessages = this.chatMessages.filter(msg => !msg.isLoading)

            this.chatMessages.push({
                type: 'bot',
                text: `✅ Flight log "${event.filename}" uploaded successfully! ` +
                      `Flight duration: ${event.flightInfo?.duration || 'Unknown'}. ` +
                      `Vehicle type: ${event.flightInfo?.vehicle_type || 'Unknown'}. ` +
                      'You can now ask questions about this flight data in the chatbot.',
                time: this.getCurrentTime()
            })

            if (this.chatbotOpen) {
                this.$nextTick(() => {
                    this.scrollToBottom()
                })
            }
        },
        handleFlightDataUploadError (event) {
            this.uploadingFile = false
            this.uploadingFilename = ''

            // Remove any existing loading messages
            this.chatMessages = this.chatMessages.filter(msg => !msg.isLoading)

            this.chatMessages.push({
                type: 'bot',
                text: `❌ Error analyzing flight log "${event.filename}": ${event.error}. ` +
                      'Please try uploading the file again.',
                time: this.getCurrentTime()
            })

            if (this.chatbotOpen) {
                this.$nextTick(() => {
                    this.scrollToBottom()
                })
            }
        },
        openPopupChatbot () {
            // Copy current messages to popup, or add welcome message if empty
            if (this.chatMessages.length > 0) {
                this.popupChatMessages = [...this.chatMessages]
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
                // Add loading message to popup
                const loadingIndex = this.popupChatMessages.length
                this.addMessageToPopup('Analyzing your question...', 'assistant', true)

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

                // Remove loading message and add response
                this.popupChatMessages.splice(loadingIndex, 1)
                this.addMessageToPopup(data.content || 'Sorry, I could not process your request.', 'assistant')

                if (data.suggested_questions && data.suggested_questions.length > 0) {
                    this.addMessageToPopup(
                        'You might also want to ask: ' + data.suggested_questions.join(', '),
                        'assistant'
                    )
                }
            } catch (error) {
                console.error('Error sending message to backend:', error)
                // Remove loading message and add error
                if (this.popupChatMessages[this.popupChatMessages.length - 1].isLoading) {
                    this.popupChatMessages.pop()
                }
                this.addMessageToPopup(
                    'Sorry, there was an error processing your request. Please try again.',
                    'assistant'
                )
            }
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
        gap: 10px;
        padding: 12px 16px;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border-radius: 12px;
        margin: 10px 6px;
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
        transition: left 0.5s;
    }

    .chatbot-toggle:hover::before {
        left: 100%;
    }

    .chatbot-toggle:hover {
        background: linear-gradient(135deg, #764ba2 0%, #667eea 100%);
        box-shadow:
            0 8px 28px rgba(102, 126, 234, 0.35),
            0 3px 12px rgba(0, 0, 0, 0.12);
        transform: translateY(-2px) scale(1.01);
        border-color: rgba(255, 255, 255, 0.3);
    }

    .chatbot-toggle:active {
        transform: translateY(-1px) scale(1.005);
        box-shadow:
            0 4px 16px rgba(102, 126, 234, 0.3),
            0 2px 6px rgba(0, 0, 0, 0.1);
    }

    .chatbot-toggle i {
        font-size: 16px;
        filter: drop-shadow(0 1px 3px rgba(0, 0, 0, 0.2));
        transition: transform 0.3s ease;
    }

    .chatbot-toggle:hover i {
        transform: scale(1.05);
    }

    .popup-button {
        background: linear-gradient(135deg, rgba(255, 255, 255, 0.3), rgba(255, 255, 255, 0.15));
        border: 1px solid rgba(255, 255, 255, 0.4);
        color: white;
        width: 32px;
        height: 32px;
        border-radius: 8px;
        cursor: pointer;
        display: flex;
        align-items: center;
        justify-content: center;
        transition: all 0.3s cubic-bezier(0.25, 0.46, 0.45, 0.94);
        margin-left: 8px;
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
        background: linear-gradient(135deg, rgba(255, 255, 255, 0.45), rgba(255, 255, 255, 0.25));
        transform: translateY(-1px) scale(1.05);
        box-shadow:
            0 4px 12px rgba(0, 0, 0, 0.18),
            inset 0 1px 0 rgba(255, 255, 255, 0.4);
        border-color: rgba(255, 255, 255, 0.6);
    }

    .popup-button:active {
        transform: translateY(0) scale(1.02);
        box-shadow:
            0 2px 6px rgba(0, 0, 0, 0.12),
            inset 0 1px 0 rgba(255, 255, 255, 0.25);
    }

    .popup-button i {
        font-size: 13px;
        filter: drop-shadow(0 1px 2px rgba(0, 0, 0, 0.25));
        transition: transform 0.2s ease;
        opacity: 0.95;
    }

    .popup-button:hover i {
        transform: scale(1.1);
        opacity: 1;
    }

    .chatbot-section {
        display: flex;
        flex-direction: column;
    }

    .chatbot-container {
        background: linear-gradient(135deg, rgba(19, 83, 136, 0.05), rgba(30, 37, 54, 0.05));
        border: 1px solid rgba(30, 37, 54, 0.15);
        border-radius: 8px;
        margin: 10px 15px;
        box-shadow: 0 4px 16px rgba(0, 0, 0, 0.1);
        overflow: hidden;
        backdrop-filter: blur(10px);
        display: flex;
        flex-direction: column;
        height: 380px; /* Fixed height to prevent sidebar resizing */
        min-height: 380px;
        max-height: 380px;
        transition: opacity 0.3s ease, transform 0.3s ease;
    }

    .chatbot-container.chatbot-visible {
        opacity: 1;
        transform: translateY(0);
    }

    .chatbot-container.chatbot-hidden {
        opacity: 0.6;
        transform: translateY(-5px);
    }

    .chatbot-placeholder {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        height: 100%;
        color: rgba(30, 37, 54, 0.5);
        font-style: italic;
        gap: 10px;
    }

    .chatbot-placeholder i {
        font-size: 32px;
        opacity: 0.3;
    }

    .chatbot-placeholder span {
        font-size: 14px;
        opacity: 0.7;
    }

    .chat-messages {
        height: 300px;
        min-height: 300px;
        max-height: 300px;
        overflow-y: auto;
        padding: 15px;
        display: flex;
        flex-direction: column;
        gap: 10px;
        background-color: rgba(255, 255, 255, 0.05);
        border-radius: 8px 8px 0 0;
        flex: 1;
    }

    .chat-message {
        display: flex;
        align-items: flex-end;
        margin-bottom: 8px;
    }

    .chat-message.user {
        justify-content: flex-end;
    }

    .chat-message.bot {
        justify-content: flex-start;
    }

    .message-bubble {
        max-width: 80%;
        padding: 8px 12px;
        border-radius: 12px;
        position: relative;
        word-wrap: break-word;
    }

    .chat-message.user .message-bubble {
        background-color: #135388;
        color: white;
        border-bottom-right-radius: 4px;
    }

    .chat-message.bot .message-bubble {
        background-color: rgba(255, 255, 255, 0.897);
        color: rgb(51, 51, 51);
        border: 1px solid rgba(30, 37, 54, 0.2);
        border-bottom-left-radius: 4px;
    }

    .message-text {
        display: block;
        font-size: 90%;
        line-height: 1.4;
    }

    .message-time {
        display: block;
        font-size: 75%;
        opacity: 0.7;
        margin-top: 4px;
        text-align: right;
    }

    .chat-message.bot .message-time {
        text-align: left;
    }

    .chat-input-container {
        display: flex;
        align-items: center;
        padding: 12px 15px;
        background: linear-gradient(135deg, rgba(19, 83, 136, 0.08), rgba(30, 37, 54, 0.08));
        border-radius: 0 0 8px 8px;
        border-top: 1px solid rgba(30, 37, 54, 0.15);
        gap: 10px;
        backdrop-filter: blur(10px);
    }

    .chat-input {
        flex: 1;
        border: 1px solid rgba(30, 37, 54, 0.25);
        border-radius: 25px;
        padding: 12px 18px;
        background: rgba(255, 255, 255, 0.95);
        color: rgb(51, 51, 51);
        font-size: 14px;
        font-weight: 400;
        outline: none;
        transition: all 0.3s ease;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
        line-height: 1.4;
    }

    .chat-input:focus {
        border-color: #135388;
        box-shadow: 0 0 0 3px rgba(19, 83, 136, 0.1), 0 4px 8px rgba(0, 0, 0, 0.1);
        background: rgba(255, 255, 255, 1);
        transform: translateY(-1px);
        animation: inputPulse 0.3s ease-out;
    }

    @keyframes inputPulse {
        0% {
            box-shadow: 0 0 0 0 rgba(19, 83, 136, 0.4);
        }
        70% {
            box-shadow: 0 0 0 6px rgba(19, 83, 136, 0);
        }
        100% {
            box-shadow: 0 0 0 3px rgba(19, 83, 136, 0.1), 0 4px 8px rgba(0, 0, 0, 0.1);
        }
    }

    .chat-input::placeholder {
        color: rgb(120, 120, 120);
        opacity: 0.8;
        font-style: italic;
    }

    .send-button {
        background: linear-gradient(135deg, #135388, #0f4369);
        color: white;
        border: none;
        border-radius: 50%;
        width: 42px;
        height: 42px;
        cursor: pointer;
        display: flex;
        align-items: center;
        justify-content: center;
        transition: all 0.3s ease;
        outline: none;
        box-shadow: 0 2px 8px rgba(19, 83, 136, 0.3);
        position: relative;
        overflow: hidden;
    }

    .send-button:not(:disabled):hover {
        background: linear-gradient(135deg, #0f4369, #0a2f4d);
        box-shadow: 0 4px 12px rgba(19, 83, 136, 0.4);
        transform: translateY(-2px);
    }

    .send-button:not(:disabled):active {
        transform: translateY(0) scale(0.95);
        box-shadow: 0 2px 6px rgba(19, 83, 136, 0.3);
    }

    .send-button::before {
        content: '';
        position: absolute;
        top: 0;
        left: -100%;
        width: 100%;
        height: 100%;
        background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.2), transparent);
        transition: left 0.5s;
    }

    .send-button:hover::before {
        left: 100%;
    }

    .send-button i {
        font-size: 16px;
        margin-left: 2px;
        z-index: 1;
        position: relative;
    }

    .send-button:disabled {
        background: linear-gradient(135deg, #ccc, #999);
        cursor: not-allowed;
        box-shadow: none;
        transform: none;
    }

    .send-button:disabled:hover {
        transform: none;
        box-shadow: none;
    }

    /* Scrollbar styling for chat messages */
    .chat-messages::-webkit-scrollbar {
        width: 6px;
    }

    .chat-messages::-webkit-scrollbar-track {
        background: rgba(0, 0, 0, 0.1);
        border-radius: 3px;
    }

    .chat-messages::-webkit-scrollbar-thumb {
        background: rgba(30, 37, 54, 0.3);
        border-radius: 3px;
    }

    .chat-messages::-webkit-scrollbar-thumb:hover {
        background: rgba(30, 37, 54, 0.5);
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
        background: linear-gradient(135deg, rgba(19, 83, 136, 0.1), rgba(30, 37, 54, 0.05)) !important;
        border: 1px solid rgba(19, 83, 136, 0.3) !important;
        position: relative;
        overflow: visible;
    }

    .loading-spinner {
        display: inline-block;
        margin-right: 8px;
        vertical-align: middle;
    }

    .spinner {
        width: 16px;
        height: 16px;
        border: 2px solid rgba(19, 83, 136, 0.3);
        border-left: 2px solid #135388;
        border-radius: 50%;
        animation: spin 1s linear infinite;
        display: inline-block;
    }

    @keyframes spin {
        0% { transform: rotate(0deg); }
        100% { transform: rotate(360deg); }
    }

    .loading-message .message-text {
        color: #135388;
        font-weight: 500;
    }

    .loading-message::after {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background: linear-gradient(90deg, transparent, rgba(19, 83, 136, 0.1), transparent);
        animation: shimmer 2s infinite;
        pointer-events: none;
    }

    @keyframes shimmer {
        0% { transform: translateX(-100%); }
        100% { transform: translateX(100%); }
    }

</style>
