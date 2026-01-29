# n8n Integration Snippets

## timestamp_snapping.js

This JavaScript code is designed to be pasted into an **n8n Code Node**.

### Prerequisites
1.  **Input 1 ("viral_clips")**: A node outputting the AI-selected clips with `start` and `end` times.
2.  **Input 2 ("aligned_words")**: A node (HTTP Request) that calls your `alignment-service` (`http://host.docker.internal:5000/align`) and returns the Whisper JSON.

### Configuration
1.  Connect the output of your AI node and your Alignment API node to the input of this Code Node.
2.  Ensure existing node names or Mode matches the `items[0]` logic. You might need to adjust `items[0]` to `$("NodeName").first().json...` depending on your n8n version and linking.
3.  The script aligns the "rough" AI timestamps to the "precise" Whisper word boundaries.
