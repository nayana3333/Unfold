// Initialize story viewer
function initStoryViewer(storyId, userStories) {
    // Start progress bar
    const progressBar = document.getElementById('storyProgress');
    const storyDuration = 10000; // 10 seconds per story
    let progress = 0;
    let progressInterval;
    
    // Start progress bar
    function startProgress() {
        progress = 0;
        progressBar.style.width = '0%';
        
        progressInterval = setInterval(function() {
            progress += 100;
            const percentage = Math.min(100, (progress / storyDuration) * 100);
            progressBar.style.width = percentage + '%';
            
            if (progress >= storyDuration) {
                clearInterval(progressInterval);
                // Go to next story or back to feed
                const nextStory = document.querySelector('.story-next');
                if (nextStory && nextStory.href) {
                    window.location.href = nextStory.href;
                } else {
                    window.location.href = document.getElementById('stories-list-url').value;
                }
            }
        }, 100);
    }
    
    // Pause progress on hover
    const storyContainer = document.querySelector('.story-container');
    if (storyContainer) {
        storyContainer.addEventListener('mouseenter', function() {
            clearInterval(progressInterval);
        });
        
        // Resume progress on mouse leave
        storyContainer.addEventListener('mouseleave', function() {
            startProgress();
        });
    }
    
    // Handle keyboard navigation
    document.addEventListener('keydown', function(e) {
        if (e.key === 'ArrowLeft') {
            // Previous story
            const prevStory = document.querySelector('.story-prev');
            if (prevStory && prevStory.href) {
                window.location.href = prevStory.href;
            }
        } else if (e.key === 'ArrowRight' || e.key === ' ') {
            // Next story or close
            const nextStory = document.querySelector('.story-next');
            if (nextStory && nextStory.href) {
                window.location.href = nextStory.href;
            } else {
                window.location.href = document.getElementById('stories-list-url').value;
            }
        } else if (e.key === 'Escape') {
            // Close stories
            window.location.href = document.getElementById('stories-list-url').value;
        }
    });
    
    // Find the current story in the user's stories
    const currentIndex = userStories.findIndex(function(story) {
        return story.id === storyId;
    });
    
    // Set up previous/next navigation if available
    const prevLink = document.querySelector('.story-prev');
    const nextLink = document.querySelector('.story-next');
    
    if (currentIndex > 0) {
        const prevStoryId = userStories[currentIndex - 1].id;
        prevLink.href = `/stories/${prevStoryId}/`;
    } else {
        prevLink.style.display = 'none';
    }
    
    if (currentIndex < userStories.length - 1) {
        const nextStoryId = userStories[currentIndex + 1].id;
        nextLink.href = `/stories/${nextStoryId}/`;
    } else {
        nextLink.href = document.getElementById('stories-list-url').value;
    }
    
    // Mark story as viewed
    fetch(`/stories/${storyId}/view/`, {
        method: 'POST',
        headers: {
            'X-CSRFTTOKEN': document.querySelector('[name=csrfmiddlewaretoken]').value,
            'X-Requested-With': 'XMLHttpRequest'
        },
        credentials: 'same-origin'
    });
    
    // Start the progress bar
    startProgress();
}
