

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
2. Label speakers as "Host" or"Guest" if you cannot identify specific names, however you should use clues to try and identify them by name.
3. Format each line as "Speaker Name: [dialogue]"
4. Preserve the original content and meaning
5. Add stage directions in [brackets] where helpful for context
6. Remove filler words like "um", "uh", "you know" for readability
7. Break long speeches into natural paragraphs
8. Maintain the original order of dialogue
9. Do not include any introductory text or explanations about what you are doing.
10. Be liberal in identifying speakers based on context, even if not explicitly stated in the transcript.
11. Do not add descriptions of visual elements- you cannot see what is happening!

Example format:
Ezra Klein: Welcome to today's show. I'm Ezra Klein here with my guest John Doe.
John Doe: Thanks for having me on the show.
Ezra Klein: Here's my first question for you...
[Discussion continues...]"""