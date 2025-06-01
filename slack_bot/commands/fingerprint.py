# commands/fingerprint.py

import asyncio
from slack_sdk.errors import SlackApiError
from slack_bolt.async_app import AsyncApp
from analysis.fingerprint import run_analysis
from config import IRIS_API_KEY, IRIS_USER
import os

def register_fingerprint_command(app: AsyncApp):

    @app.command("/fingerprint")
    async def handle_fingerprint_command(ack, say, command, client):
        await ack()

        channel_id = command['channel_id']

        # Try to join the channel if not already in it
        if not await ensure_bot_in_channel(client, channel_id, say):
            return

        # Extract the search hash, limit, and empty flag from the command text
        text = command['text'].strip()

        if not text:
            await say("Please provide a search hash. Usage: /fingerprint [-limit <percentage>] [-empty] <search_hash>")
            return

        # Default limit percentage and include_empty flag
        limit_percentage = 10
        include_empty = False

        # Parse the command text
        args = text.split()
        search_hash = None

        # Process flags
        i = 0
        while i < len(args):
            if args[i] == '-limit':
                try:
                    limit_percentage = float(args[i + 1])
                    i += 2
                except (ValueError, IndexError):
                    await say("Invalid limit value. Please provide a number after '-limit'.")
                    return
            elif args[i] == '-empty':
                include_empty = True
                i += 1
            else:
                search_hash = args[i]
                i += 1

        if not search_hash:
            await say("Please provide a search hash after the flags. Usage: /fingerprint [-limit <percentage>] [-empty] <search_hash>")
            return

        try:
            # Run the analysis with the specified limit percentage and include_empty flag
            document = await asyncio.get_event_loop().run_in_executor(
                None,
                run_analysis,
                search_hash,
                limit_percentage,
                IRIS_API_KEY,
                IRIS_USER,
                include_empty
            )

            # Save the report to a docx file
            file_name = 'analysis_results.docx'
            document.save(file_name)

            # Upload the file to Slack
            with open(file_name, 'rb') as file_content:
                result = await client.files_upload_v2(
                    channels=channel_id,
                    file=file_content,
                    filename='analysis_results.docx',
                    title='Iris Investigate Analysis Report',
                    initial_comment=f"Here's the analysis report based on your search hash with a correlation limit of {limit_percentage}%:"
                )
            if not result.get('file'):
                await say("The report was generated, but there was an issue uploading it.")

            # Delete the local file after uploading
            os.remove(file_name)

        except Exception as e:
            await say(f"An error occurred during analysis: {str(e)}")

    async def ensure_bot_in_channel(client, channel_id, say):
        try:
            await client.chat_postMessage(channel=channel_id, text="Processing your request. This may take a few moments...")
            return True
        except SlackApiError as e:
            if e.response['error'] == 'not_in_channel':
                if await join_channel(client, channel_id):
                    await client.chat_postMessage(channel=channel_id, text="I've joined the channel. Processing your request. This may take a few moments...")
                    return True
                else:
                    await say("I couldn't join the channel. Please add me to this channel and try again.")
                    return False
            else:
                await say(f"An error occurred: {str(e)}")
                return False

    async def join_channel(client, channel_id):
        try:
            await client.conversations_join(channel=channel_id)
            return True
        except SlackApiError as e:
            print(f"Error joining channel: {e}")
            return False
