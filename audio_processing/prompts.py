

def get_tag_suggestion_prompt(tag_list, transcript_excerpt):
    import json
    
    return f"""You are an AI assistant that analyzes podcast transcripts and suggests relevant tags.

Available tags:
{json.dumps(tag_list, indent=2)}

Podcast transcript (first 2000 characters):
{transcript_excerpt}

Based on the transcript content, please suggest which tags are most relevant.
Return ONLY a JSON array of tag IDs (numbers) that apply to this podcast.
Example: [1, 3, 7]

Consider the topic, genre, subject matter, and themes discussed in the podcast.

Again, you should respond only with a JSON array of tag IDs.
Do not include any additional text or explanations."""


def get_content_analysis_prompt(transcript_excerpt):
    return f"""Analyze this podcast transcript and provide a brief summary of the main topics, themes, and genre.

Transcript:
{transcript_excerpt}

Please provide:
1. Main topic/subject
2. Genre (e.g., interview, educational, storytelling, news, etc.)
3. Key themes discussed
4. Target audience

Keep your response concise and factual."""

def get_speaker_transcript_prompt(transcript_excerpt):
    """
    Generate a prompt for converting a transcript into a speaker-formatted script.
    
    Args:
        transcript_excerpt: The podcast transcript to format
    
    Returns:
        str: Formatted prompt for speaker identification and script formatting
    """
    return f"""You are an AI assistant that converts podcast transcripts into properly formatted scripts with speaker identification.

Original transcript:
{transcript_excerpt}

Please rewrite this transcript as a script format with identified speakers. Follow these guidelines:

1. Identify different speakers as best as you can from context clues, speaking patterns, and content
2. Label speakers as "Host", "Guest", "Speaker 1", "Speaker 2", etc. based on their apparent roles
3. Format each line as "Speaker Name: [dialogue]"
4. Preserve the original content and meaning
5. Add stage directions in [brackets] where helpful for context
6. Remove filler words like "um", "uh", "you know" for readability
7. Break long speeches into natural paragraphs

Example format:
Host: Welcome to today's show. We're here with our special guest.
Guest: Thanks for having me on the show.
Host: Let's dive right into our main topic today.
[Discussion continues...]

Please provide the complete formatted script below:"""