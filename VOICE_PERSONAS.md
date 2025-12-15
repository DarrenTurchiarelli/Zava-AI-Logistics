# Azure AI Speech Voice Personas Guide

## Overview

The DT Logistics application supports multiple high-quality neural voice personas from Azure AI Speech Services. These voices use advanced neural text-to-speech technology for natural, human-like speech that's much less robotic than standard voices.

## Setup

### 1. Enable Azure Speech Services

Add these environment variables to your `.env` file:

```env
AZURE_SPEECH_KEY="your-speech-service-key"
AZURE_SPEECH_REGION="australiaeast"
AZURE_SPEECH_VOICE="william"  # Optional - defaults to william
```

### 2. Get Azure Speech Service Key

1. Go to [Azure Portal](https://portal.azure.com)
2. Create a **Speech Service** resource (or use existing one)
3. Navigate to **Keys and Endpoint**
4. Copy **Key 1** to `AZURE_SPEECH_KEY`
5. Set **Location/Region** to `AZURE_SPEECH_REGION`

## Available Voice Personas

All voices are Australian English neural voices with different personalities and speaking styles:

### Professional & Business

| Persona | Gender | Description | Best For |
|---------|--------|-------------|----------|
| **william** ⭐ | Male | Clear, confident professional voice | Default - General use, professional contexts |
| **freya** | Female | Professional, articulate business voice | Business communications, formal announcements |
| **ken** | Male | Deep, resonant commanding voice | Authority figures, important announcements |
| **neil** | Male | Calm, measured instructional voice | Tutorials, step-by-step instructions |

### Friendly & Conversational

| Persona | Gender | Description | Best For |
|---------|--------|-------------|----------|
| **natasha** | Female | Warm, friendly customer service voice | Customer interactions, support |
| **darren** | Male | Warm, trustworthy narrator voice | Storytelling, guidance |
| **carly** | Female | Natural, conversational casual voice | Informal interactions, relatable content |
| **joanne** | Female | Mature, authoritative yet friendly | Experienced advisor, mentorship |

### Energetic & Engaging

| Persona | Gender | Description | Best For |
|---------|--------|-------------|----------|
| **annette** | Female | Cheerful, energetic upbeat voice | Marketing, promotional content |
| **duncan** | Male | Young, enthusiastic modern voice | Youth-oriented content, dynamic announcements |
| **kim** | Female | Bright, clear excellent clarity | Clear communication, important information |

### Calm & Empathetic

| Persona | Gender | Description | Best For |
|---------|--------|-------------|----------|
| **elsie** | Female | Gentle, calm soothing voice | Customer care, sensitive communications |

### Versatile

| Persona | Gender | Description | Best For |
|---------|--------|-------------|----------|
| **tina** | Male | Versatile, adaptable voice | Multi-purpose use cases |

## How to Change Voice Persona

### Method 1: Environment Variable (Recommended)

Set in your `.env` file:

```env
AZURE_SPEECH_VOICE="darren"  # Use any persona name from the list
```

Then restart your application.

### Method 2: API Endpoint

Change voice dynamically via API:

```javascript
// Get list of available voices
fetch('/api/speech/voices')
  .then(res => res.json())
  .then(data => console.log(data.voices));

// Change to a different voice
fetch('/api/speech/voice', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ persona: 'natasha' })
})
  .then(res => res.json())
  .then(data => console.log('Voice changed:', data));
```

### Method 3: Programmatically

```python
from services.speech import get_speech_service

# Get service with specific voice
speech_service = get_speech_service(voice_persona='darren')

# Change voice later
speech_service.set_voice_persona('natasha')

# List all available voices
from services.speech import AzureSpeechService
voices = AzureSpeechService.list_available_voices()
```

## Testing Different Voices

To find the best voice for your application:

1. **Start with the default**: `william` is a balanced, professional choice
2. **Consider your audience**: 
   - Customer-facing? Try `natasha` or `carly`
   - Instructions/tutorials? Try `neil` or `freya`
   - Marketing/energetic? Try `annette` or `duncan`
3. **Test with actual content**: Different voices sound better with different types of content
4. **Get user feedback**: What sounds natural to you may differ for others

## Voice Quality Notes

- All voices use **Neural TTS** technology for natural, human-like speech
- Voices support **prosody** (natural rhythm, stress, and intonation)
- **Multilingual** capabilities (though configured for Australian English)
- **Low latency** - suitable for real-time applications
- **High quality** audio at 24kHz or 48kHz

## Troubleshooting

### Voice sounds robotic
- Ensure you're using a **Neural** voice (all personas listed are neural)
- Check your Azure Speech Service is in a supported region
- Verify your `AZURE_SPEECH_KEY` is correct

### Voice not changing
- Restart the application after changing `.env`
- Check the console for voice persona confirmation message
- Verify persona name is spelled correctly (case-insensitive)

### Speech not working
- Confirm `AZURE_SPEECH_KEY` and `AZURE_SPEECH_REGION` are set
- Check Azure Speech Service quota/usage
- Look for error messages in the console

## Cost Considerations

Azure Neural TTS pricing (as of 2024):
- **Standard**: ~$16 per 1 million characters
- **Neural**: ~$16 per 1 million characters (same price, better quality!)

Tips to optimize costs:
- Cache commonly used phrases
- Use streaming for long content
- Consider batch processing for bulk operations

## More Information

- [Azure Speech Service Documentation](https://learn.microsoft.com/azure/ai-services/speech-service/)
- [Neural Voice Gallery](https://speech.microsoft.com/portal/voicegallery)
- [SSML Reference](https://learn.microsoft.com/azure/ai-services/speech-service/speech-synthesis-markup) - Advanced voice control
