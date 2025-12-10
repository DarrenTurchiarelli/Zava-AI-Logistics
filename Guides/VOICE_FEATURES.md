# 🎤 Voice-Enabled AI Customer Service Chatbot

## Overview
The customer service chatbot now supports **multimodal interactions** with voice input (speech-to-text) and voice output (text-to-speech), making it easier and faster for customer service representatives to interact with the AI assistant hands-free.

## Features

### 🎤 Voice Input (Speech-to-Text)
- **Click the microphone button** to start voice recognition
- Speak naturally - the system will transcribe your speech
- Button turns red and pulses while listening
- Automatically sends your message when you finish speaking
- Works in Chrome, Edge, Safari, and other modern browsers

### 🔊 Voice Output (Text-to-Speech)
- AI responses are automatically read aloud
- Toggle auto-speak on/off with the checkbox
- Click the mute button to stop speaking at any time
- Uses natural-sounding voices when available
- Cleans markdown and special characters for better speech quality

### ✨ Visual Indicators
- **Listening Status**: Badge appears in header when microphone is active
- **Pulsing Microphone**: Red pulsing button while recording
- **Animated Transitions**: Smooth animations for better UX

## How to Use

### Voice Input
1. Navigate to **Customer Service Chatbot** page
2. Click the **🎤 microphone button** (blue button next to Send)
3. Allow microphone access if prompted by browser
4. Speak your question clearly (e.g., "Where is parcel DTVIC123?")
5. The system will transcribe and automatically send your message

### Voice Output
1. AI responses are **automatically spoken** by default
2. Uncheck **"Auto-speak responses"** to disable voice output
3. Click the **🔇 mute button** to stop current speech

### Keyboard Input (Still Available)
- Type questions as before
- Press Enter to send
- Voice and text input work seamlessly together

## Sample Voice Commands

Try these natural language commands:
- "Track parcel DTVIC123"
- "Show me recent fraud reports"
- "How many parcels are in transit?"
- "What's the status of deliveries to Sydney?"
- "Find parcel at distribution center"

## Browser Compatibility

### Voice Input (Speech Recognition)
✅ **Chrome** - Full support  
✅ **Microsoft Edge** - Full support  
✅ **Safari** - Full support (macOS, iOS)  
⚠️ **Firefox** - Limited support (requires flag)  
❌ **Internet Explorer** - Not supported  

### Voice Output (Speech Synthesis)
✅ All modern browsers support text-to-speech

## Technical Details

### Web Speech API
- Uses **Web Speech API** for speech recognition
- Uses **Speech Synthesis API** for text-to-speech
- Language: English (en-US)
- Continuous listening: Disabled (one command at a time)
- Interim results: Disabled (only final transcript)

### Speech Parameters
- **Rate**: 1.0 (normal speed)
- **Pitch**: 1.0 (natural pitch)
- **Volume**: 1.0 (full volume)
- **Voice**: Prefers natural/premium voices when available

### Text Cleaning for Speech
The system automatically cleans AI responses before speaking:
- Removes markdown formatting (`**bold**`, `# headers`)
- Removes HTML tags
- Removes code backticks
- Keeps only natural language text

## Privacy & Security

### Microphone Access
- Browser requires user permission for microphone access
- Permission is requested on first use
- Permission persists across sessions (browser setting)
- No audio is recorded or stored - only transcribed text

### Data Processing
- Speech recognition happens in the browser (client-side)
- No voice data sent to external servers
- Only transcribed text is sent to backend AI agent

## Troubleshooting

### Microphone Not Working
1. Check browser permissions (Settings → Privacy → Microphone)
2. Ensure microphone is not used by another application
3. Try refreshing the page
4. Check browser console for error messages

### No Speech Output
1. Check browser volume settings
2. Verify "Auto-speak responses" is checked
3. Try a different browser
4. Check if sound is muted system-wide

### Speech Recognition Errors
- **"no-speech"**: Speak louder or move closer to microphone
- **"not-allowed"**: Grant microphone permissions in browser settings
- **"network"**: Check internet connection (some browsers use cloud API)

## Accessibility Benefits

### For Customer Service Reps
- **Hands-free operation** while typing or reviewing screens
- **Faster input** for complex tracking numbers
- **Multitasking** - listen to responses while working
- **Reduced typing** strain for frequent users

### For All Users
- **Screen reader friendly** - works with existing accessibility tools
- **Visual indicators** for hearing-impaired users
- **Audio feedback** for visually-impaired users
- **Flexible modes** - choose voice, text, or both

## Future Enhancements (Potential)

- [ ] Multi-language support (Spanish, French, etc.)
- [ ] Voice commands for quick actions (e.g., "Clear chat")
- [ ] Custom wake word detection ("Hey Assistant")
- [ ] Voice authentication for secure operations
- [ ] Sentiment analysis from voice tone
- [ ] Azure Speech Services integration for advanced features
- [ ] Offline speech recognition support
- [ ] Voice profile customization (speed, pitch preferences)

## Code References

### Frontend Files
- **Template**: `templates/customer_service_chatbot.html`
  - Voice recognition initialization (lines 130-180)
  - Speech synthesis functions (lines 180-230)
  - UI controls and animations (CSS section)

### Backend Files
- **Chatbot Logic**: `customer_service_chatbot.py`
  - AI agent integration (unchanged - voice is client-side)

## Demo Workflow

1. **Login** as customer service rep (`support` / `demo123`)
2. Navigate to **Customer Service Chatbot**
3. **Click microphone** button
4. **Say**: "Show me parcels in transit"
5. **Listen** as AI responds with voice + text
6. **Try typing** a follow-up question
7. **Toggle** auto-speak on/off to test both modes

---

**Note**: Voice features are client-side enhancements that work with the existing AI agent backend. No backend changes were required to add multimodal capabilities!
