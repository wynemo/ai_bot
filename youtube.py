from typing import Dict, Optional, Tuple
import yt_dlp
from yt_dlp.utils import YoutubeDLError
import json
import os
import requests
import webvtt
import re


CACHE_DIR = './cache'

def ensure_cache_dir():
    if not os.path.exists(CACHE_DIR):
        os.makedirs(CACHE_DIR, exist_ok=True)
    if not os.path.isdir(CACHE_DIR):
        raise ValueError(f'{CACHE_DIR} is not a directory')

def validate_youtube_url(url: str) -> bool:
    try:
        video_id = yt_dlp.extractor.youtube.YoutubeIE.extract_id(url)
        return True
    except YoutubeDLError:
        return False

class VideoExtractor:
    def __init__(self, proxy: Optional[str] = None):
        ensure_cache_dir()

        self.ydl_opts = {
            'writesubtitles': True,
            'writeannotations': True,
            'writeautomaticsub': True,
            'subtitleslangs': ['en', 'en-US', 'en-CA'],  # Focus on English captions for now
            'skip_download': True,  # Don't download the video file
            'quiet': False,
            'no_warnings': False,
            'no-playlist': True
        }

        if proxy:
            print(f'Setting proxy: {proxy[:10]}...')
            self.ydl_opts['proxy'] = proxy

    def get_captions_by_priority(self, info: Dict) -> Optional[Dict]:
        """
        Get captions based on priority order:
        1. Manual subtitles (en-US, en-CA, en-*)
        2. Automatic captions (en-orig, en-US, en-CA, en)

        Args:
            info: Video information dictionary from yt-dlp

        Returns:
            Caption json blob (fields ext, url, name)
        """
        # Priority order for subtitle languages
        subtitle_priorities = ['en-US', 'en-CA', 'en']
        auto_caption_priorities = ['en-orig', 'en-US', 'en-CA', 'en']
        format_priorities = ['vtt', 'srt', 'ttml']

        caption_track = None

        # Check manual subtitles first
        if info.get('subtitles'):
            print("text---", info["subtitles"])
            # Check specific language variants first
            for lang in subtitle_priorities:
                if lang in info['subtitles']:
                    caption_track = info['subtitles'][lang]
                    break

            # Then check for any other en-* variants
            else:
                for lang in info['subtitles'].keys():
                    if lang.startswith('en-') or lang.startswith('zh-'):
                        caption_track = info['subtitles'][lang]
                        break

        # Check automatic captions if no manual subtitles found
        if not caption_track:
            if info.get('automatic_captions'):
                for lang in auto_caption_priorities:
                    if lang in info['automatic_captions']:
                        caption_track = info['automatic_captions'][lang]
                        break

        if not caption_track:
            return None

        # Find the preferred format
        for format in format_priorities:
            for track in caption_track:
                if not 'name' in track or track.get('protocol') == 'm3u8_native': # skip weird m3u8 captions
                    continue
                if track.get('ext') == format:
                    return track

        # If no compatible format found, fail
        return None

    def download_captions(self, video_id: str, caption_obj: Dict) -> str:
        ext = caption_obj['ext']
        url = caption_obj['url']
        cache_file = os.path.join(CACHE_DIR, video_id + '.' + ext)

        if os.path.isfile(cache_file):
            return open(cache_file).read()

        # Download caption content
        response = requests.get(url)
        response.raise_for_status()
        content = response.text

        with open(cache_file, 'w') as f:
            f.write(content)

        return content

    def _timestamp_to_seconds(self, timestamp: str) -> float:
        """
        Convert WebVTT timestamp to seconds.

        Args:
            timestamp: WebVTT timestamp in format "HH:MM:SS.mmm"

        Returns:
            Float representing total seconds
        """
        time_parts = timestamp.split(':')
        hours = float(time_parts[0])
        minutes = float(time_parts[1])
        seconds = float(time_parts[2])

        return hours * 3600 + minutes * 60 + seconds

    def _seconds_to_timestamp(self, total_seconds: float) -> str:
        """
        Convert seconds to WebVTT timestamp.

        Args:
            total_seconds: Float representing total seconds

        Returns:
            WebVTT timestamp in format "HH:MM:SS.mmm"
        """
        hours = int(total_seconds // 3600)
        remaining = total_seconds % 3600
        minutes = int(remaining // 60)
        seconds = remaining % 60

        # Format with leading zeros and exactly 3 decimal places
        return f"{hours:02d}:{minutes:02d}:{seconds:06.3f}"

    # because webvtt's shit doesn't include fractional part (the milliseconds), causing fucking problems !!
    def _ts_to_secs(self, timestamp):
        return timestamp.in_seconds() + (timestamp.milliseconds / 1000)

    # adapted from https://github.com/bindestriche/srt_fix/blob/5b4442a8cdcae06c53545f4d0c99c3e624416919/simplesrt.py#L132C1-L201C28
    def dedupe_yt_captions(self, subs_iter):
        previous_subtitle = None
        text = ""
        for subtitle in subs_iter:

            if previous_subtitle is None: # first interation set previous subtitle for comparison
                 previous_subtitle = subtitle
                 continue

            subtitle.text = subtitle.text.strip() # remove trailing linebreaks

            if len(subtitle.text) == 0:  # skip over empty subtitles
                continue

            if (self._ts_to_secs(subtitle.start_time) - self._ts_to_secs(subtitle.end_time) < 0.15 and # very short
                    subtitle.text in previous_subtitle.text ): # same text as previous
                previous_subtitle.end = subtitle.end # lengthen previous subtitle
                continue

            current_lines = subtitle.text.split("\n")
            last_lines = previous_subtitle.text.split("\n")

            singleword=False

            if current_lines[0] == last_lines[-1]: # if first current is  last previous
                if len(last_lines)==1:
                    if  len(last_lines[0].split(" "))<2 and len(last_lines[0])>2: # if  is just one word
                        singleword=True
                        subtitle.text= current_lines[0]+" "+"\n".join(current_lines[1:]) # remove line break after single word

                    else:
                        subtitle.text = "\n".join(current_lines[1:]) # discard first line of current
                else:
                    subtitle.text = "\n".join(current_lines[1:]) # discard first line of current
            else: # not fusing two lines
                if len(subtitle.text.split(" "))<=2: # only one word in subtitle

                    previous_subtitle.end = subtitle.end # lengthen previous subtitle
                    title_text=subtitle.text
                    if title_text[0]!=" ":
                        title_text=" "+title_text

                    previous_subtitle.text+=title_text # add text to previous
                    continue # drop this subtitle


            if self._ts_to_secs(subtitle.start_time) <= self._ts_to_secs(previous_subtitle.end_time): # remove overlap and let 1ms gap
                new_time = max(self._ts_to_secs(subtitle.start_time) - 0.001, 0)
                previous_subtitle.end = self._seconds_to_timestamp(new_time)
            if self._ts_to_secs(subtitle.start_time) >= self._ts_to_secs(subtitle.end_time): # swap start and end if wrong order
                subtitle.start, subtitle.end = subtitle.end, subtitle.start


            if not singleword:
                yield previous_subtitle
            previous_subtitle = subtitle
        yield previous_subtitle


    def parse_captions(self, ext: str, content: str) -> str:
        """
        Parse caption content with formatting based on timing.

        Args:
            ext: Captions file extension
            content: Downloaded captions content

        Returns:
            Plain text of the captions with paragraph breaks for pauses > 3 seconds

        Raises:
            ValueError: If caption format is not supported
        """

        if ext == 'vtt':
            captions = webvtt.from_string(content)
            result = ''

            captions = list(self.dedupe_yt_captions(captions))

            for i, caption in enumerate(captions):
                # Clean up the current caption text
                current_text = caption.text.replace('\n', ' ').strip()


                if i > 0:
                    # Calculate time difference with previous caption
                    prev_end = self._timestamp_to_seconds(captions[i-1].end)
                    current_start = self._timestamp_to_seconds(caption.start)
                    time_diff = current_start - prev_end

                    # Add double newline for pauses > 3 seconds, space otherwise
                    if time_diff >= 2:
                        result += '\n\n'
                    elif time_diff >= 1:
                        result += '\n'
                    else:
                        result += ' '

                result += current_text
        else:
            raise ValueError(f"Unsupported caption format: {ext}")

        # Final cleanup to remove any multiple spaces
        result = ' '.join(re.split(' +', result))

        return result

    def extract_video_info(self, url: str) -> Tuple[Optional[Dict], Optional[str]]:
        """
        Extract video description and captions from a YouTube URL.

        Args:
            url: YouTube video URL

        Returns:
            Tuple containing:
            - Dictionary with video information (title, description)
            - String containing the captions/subtitles
        """

        video_id = yt_dlp.extractor.youtube.YoutubeIE.extract_id(url)

        cache_file = os.path.join(CACHE_DIR, video_id + '.json')
        if os.path.isfile(cache_file):
            print(f'Reusing cached file: {cache_file}')
            return json.load(open(cache_file))

        try:
            with yt_dlp.YoutubeDL(self.ydl_opts) as ydl:
                # Get video info
                video_info = ydl.extract_info(f'https://youtube.com/watch?v={video_id}', download=False)
                video_id = video_info['id']
        except YoutubeDLError as e:
            print(f"Error extracting video information: {str(e)}")
            return None, None

        with open(cache_file, 'w') as f:
            json.dump(video_info, f, indent=4)

        return video_info

def get_video_caption(url):
    try:
        extractor = VideoExtractor(proxy=None)

        # Download metadata
        video_info = extractor.extract_video_info(url)
        if not video_info:
            raise ValueError("failed to download video info")

        video_id = video_info['id']

        # Get captions
        caption_track = extractor.get_captions_by_priority(video_info)
        ext = caption_track['ext']
        print(f'Using captions track: {caption_track['name']} ({ext})')

        # Download captions
        downloaded_content = extractor.download_captions(video_id, caption_track)

        # Download and parse captions
        caption_text = extractor.parse_captions(ext, downloaded_content)

        return caption_text
    except Exception:
        return None



if __name__ == "__main__":
    get_video_caption("https://youtu.be/O3pmEyVo0J8")
