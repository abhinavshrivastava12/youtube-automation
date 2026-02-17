import os
from dotenv import load_dotenv
from script_generator import generate_script
from video_creator import create_video
from youtube_uploader import upload_to_youtube
from notifier import send_notification

load_dotenv()

def main():
    print("=" * 50)
    print("YouTube Automation Tool")
    print("=" * 50)
    
    # Video type selection
    print("\nSelect video type:")
    print("1. Tech Review")
    print("2. Educational/Tutorial")
    print("3. Top 10 List")
    print("4. News Summary")
    print("5. Motivational")
    print("6. Custom Topic")
    
    choice = input("\nEnter choice (1-6): ")
    
    video_types = {
        "1": "Tech Review",
        "2": "Educational Tutorial",
        "3": "Top 10 List",
        "4": "News Summary",
        "5": "Motivational Speech",
        "6": "Custom"
    }
    
    video_type = video_types.get(choice, "Custom")
    
    if video_type == "Custom":
        topic = input("Enter your custom topic: ")
    else:
        topic = input(f"Enter specific topic for {video_type}: ")
    
    print(f"\n🤖 Generating script for: {topic}")
    
    # Step 1: Generate Script
    script_data = generate_script(topic, video_type)
    print(f"✅ Script generated: {script_data['title']}")
    
    # Step 2: Create Video
    print("\n🎬 Creating video...")
    video_path = create_video(script_data)
    print(f"✅ Video created: {video_path}")
    
    # Step 3: Upload to YouTube
    print("\n📤 Uploading to YouTube...")
    video_id = upload_to_youtube(
        video_path,
        script_data['title'],
        script_data['description'],
        script_data['tags']
    )
    print(f"✅ Video uploaded! ID: {video_id}")
    
    # Step 4: Send Notification
    video_url = f"https://youtube.com/watch?v={video_id}"
    send_notification(script_data['title'], video_url)
    print(f"\n🎉 Done! Video URL: {video_url}")

if __name__ == "__main__":
    main()