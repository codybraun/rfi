

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

def get_speaker_transcript_prompt(speaker_name, transcript_excerpt):
    return f"""From this podcast transcript, extract the parts spoken by the various speakers as well as you can.

You may not be able to identify all speakers, but do your best. You can label them speaker1, speaker2, etc. if you don't know their names.

Structure it like this:

Speaker 1: Dialogue from speaker 1
Speaker 2: Dialogue from speaker 2
etc.
"""