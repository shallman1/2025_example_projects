# commands/track.py

import asyncio
import os
from slack_sdk.errors import SlackApiError
from slack_bolt.async_app import AsyncApp
from config import IRIS_API_KEY, IRIS_USER
from utils.api_utils import query_iris_api
from utils.data_utils import save_results_to_csv

def register_track_command(app: AsyncApp):

    @app.command("/track")
    async def handle_track_command(ack, say, command, client):
        await ack()

        channel_id = command['channel_id']
        user_id = command['user_id']

        # Try to join the channel if not already in it
        if not await ensure_bot_in_channel(client, channel_id, say):
            return

        # Extract the search hash from the command text
        text = command['text'].strip()

        if not text:
            await say("Please provide a search hash. Usage: /track <search_hash>")
            return

        search_hash = text

        # Filename based on user_id
        csv_filename = f"{user_id}_track.csv"

        # Check if the user already has an active tracking
        if os.path.exists(csv_filename):
            await say("You already have an active tracking. Starting a new track will overwrite your previous tracking.")
            # Optionally, you can prompt the user to confirm overwriting
            # For simplicity, we'll proceed to overwrite
            # Alternatively, you could return here and ask the user to stop tracking first
            # await say("Please use /stop_tracking before starting a new one.")
            # return

        try:
            # Query the Iris Investigate API with the search_hash
            results = await query_iris_api(IRIS_API_KEY, IRIS_USER, search_hash)

            # Save the results to a CSV file, including the search_hash
            save_results_to_csv(csv_filename, search_hash, results)

            # Let the user know that tracking has started
            await say(f"Tracking started for search_hash `{search_hash}`. You will be notified of any changes.")

        except Exception as e:
            await say(f"An error occurred while starting tracking: {str(e)}")

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
