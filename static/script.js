document.addEventListener('DOMContentLoaded', () => {
    const songNameInput = document.getElementById('songName');
    const searchBtn = document.getElementById('searchBtn');
    const qualitySelect = document.getElementById('quality');
    const errorDiv = document.getElementById('error');
    const searchResultsDiv = document.getElementById('searchResults');
    const resultsListDiv = document.getElementById('resultsList');

    const showError = (message) => {
        errorDiv.textContent = message;
        errorDiv.classList.remove('hidden');
        setTimeout(() => {
            errorDiv.classList.add('hidden');
        }, 3000);
    };

    const downloadSong = async (url, songInfo) => {
        try {
            if (!url) {
                showError('无效的下载链接，请重试');
                return;
            }
            
            const encodedSongInfo = encodeURIComponent(JSON.stringify(songInfo));
            const response = await fetch(`/api/download?url=${encodeURIComponent(url)}&song_info=${encodedSongInfo}`);
            const result = await response.json();
            
            if (result.code === 200) {
                showSuccess(`下载成功：${result.data.filename}`);
            } else {
                showError('下载失败，请稍后重试');
            }
        } catch (err) {
            showError('下载失败，请稍后重试');
        }
    };

    const createSongCard = (song) => {
        const timeToSeconds = (timeStr) => {
            const [minutes, seconds] = timeStr.split(':').map(num => parseInt(num));
            return minutes * 60 + seconds;
        };

        const durationInSeconds = timeToSeconds(song.interval);

        const card = document.createElement('div');
        card.className = 'p-4 border rounded-lg hover:shadow-md transition-shadow';
        card.innerHTML = `
            <div class="flex gap-4">
                <img 
                    src="${song.cover}" 
                    alt="${song.song}"
                    class="w-24 h-24 rounded-lg object-cover"
                    onerror="this.src='data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 width=%22100%22 height=%22100%22><rect width=%22100%22 height=%22100%22 fill=%22%23ddd%22/></svg>'"
                >
                <div class="flex-1">
                    <h3 class="text-lg font-semibold">${song.song}</h3>
                    <p class="text-gray-600">${song.singer}</p>
                    <p class="text-gray-500 text-sm">
                        专辑：${song.album}<br>
                        时长：${song.interval}<br>
                        音质：${song.quality}
                    </p>
                    <div class="flex flex-col gap-2 mt-2">
                        <div class="flex items-center gap-2">
                            <button
                                data-play-id="${song.id}"
                                onclick='playMusic("${song.url}", "${song.id}", ${durationInSeconds})'
                                class="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 flex items-center gap-2 text-sm"
                            >
                                <i class="ri-play-line"></i>
                                <span>播放</span>
                            </button>
                            <button
                                onclick='downloadSong("${song.url}", ${JSON.stringify(song).replace(/'/g, "\\'")});'
                                class="px-4 py-2 bg-green-500 text-white rounded-lg hover:bg-green-600 flex items-center gap-2 text-sm"
                            >
                                <i class="ri-download-line"></i>
                                下载
                            </button>
                            <span class="text-sm text-gray-500" data-time-id="${song.id}">00:00 / ${song.interval}</span>
                        </div>
                        <div class="flex-1 h-2 bg-gray-200 rounded-full overflow-hidden cursor-pointer" 
                             data-progress-container="${song.id}"
                             style="touch-action: none;">
                            <div class="h-full bg-blue-500 rounded-full transition-all duration-100" 
                                 data-progress="${song.id}" 
                                 style="width: 0%"></div>
                        </div>
                    </div>
                </div>
            </div>
        `;
        return card;
    };

    const formatTime = (timeStr) => {
        if (typeof timeStr === 'number') {
            const minutes = Math.floor(timeStr / 60);
            const seconds = Math.floor(timeStr % 60);
            return `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
        } else if (typeof timeStr === 'string') {
            const [minutes, seconds] = timeStr.split(':').map(num => parseInt(num));
            return `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
        }
        return '00:00';
    };

    const updateProgress = (id, currentTime, duration) => {
        console.log(`Updating progress for id: ${id}, currentTime: ${currentTime}, duration: ${duration}`);
        const progressBar = document.querySelector(`[data-progress="${id}"]`);
        const timeDisplay = document.querySelector(`[data-time-id="${id}"]`);
        const progressContainer = document.querySelector(`[data-progress-container="${id}"]`);

        if (progressBar && timeDisplay) {
            const durationInSeconds = typeof duration === 'string' ?
                duration.split(':').reduce((acc, time) => (60 * acc) + +time, 0) :
                duration;

            const progress = (currentTime / durationInSeconds) * 100;
            progressBar.style.width = `${Math.min(100, Math.max(0, progress))}%`;
            timeDisplay.textContent = `${formatTime(currentTime)} / ${formatTime(duration)}`;
        }

        if (progressContainer && !isDragging) {
            progressContainer.onmousedown = (e) => {
                isDragging = true;
                currentDraggingId = id;
                updateProgressFromEvent(e, progressContainer, id);

                document.addEventListener('mousemove', handleMouseMove);
                document.addEventListener('mouseup', handleMouseUp);
            };
        }
    };

    const handleMouseMove = (e) => {
        if (isDragging && currentDraggingId) {
            const progressContainer = document.querySelector(`[data-progress-container="${currentDraggingId}"]`);
            if (progressContainer) {
                updateProgressFromEvent(e, progressContainer, currentDraggingId);
            }
        }
    };

    const handleMouseUp = () => {
        if (isDragging && currentDraggingId) {
            isDragging = false;
            const progressContainer = document.querySelector(`[data-progress-container="${currentDraggingId}"]`);
            if (progressContainer && audioPlayer) {
                const rect = progressContainer.getBoundingClientRect();
                const percentage = (event.clientX - rect.left) / rect.width;
                audioPlayer.currentTime = percentage * audioPlayer.duration;
            }
            currentDraggingId = null;
        }
        document.removeEventListener('mousemove', handleMouseMove);
        document.removeEventListener('mouseup', handleMouseUp);
    };

    const updateProgressFromEvent = (e, container, id) => {
        const rect = container.getBoundingClientRect();
        const x = Math.max(0, Math.min(e.clientX - rect.left, rect.width));
        const percentage = (x / rect.width) * 100;

        const progressBar = document.querySelector(`[data-progress="${id}"]`);
        if (progressBar) {
            progressBar.style.width = `${percentage}%`;
        }

        if (audioPlayer) {
            const newTime = (percentage / 100) * audioPlayer.duration;
            const timeDisplay = document.querySelector(`[data-time-id="${id}"]`);
            if (timeDisplay) {
                timeDisplay.textContent = `${formatTime(newTime)} / ${formatTime(audioPlayer.duration)}`;
            }
        }
    };

    const searchSong = async () => {
        const songName = songNameInput.value.trim();
        if (!songName) {
            showError('请输入歌曲名称');
            return;
        }

        searchBtn.disabled = true;
        try {
            const searchCount = document.getElementById('searchCount').value;
            const response = await fetch(
                `/api/search?word=${encodeURIComponent(songName)}&q=${qualitySelect.value}&count=${searchCount}`
            );
            const data = await response.json();

            if (data.code === 200 && data.data && data.data.length > 0) {
                resultsListDiv.innerHTML = '';
                data.data.forEach(song => {
                    resultsListDiv.appendChild(createSongCard(song));
                });
                searchResultsDiv.classList.remove('hidden');
            } else {
                showError('未找到歌曲');
                searchResultsDiv.classList.add('hidden');
            }
        } catch (err) {
            showError('搜索出错，请稍后重试');
            searchResultsDiv.classList.add('hidden');
        } finally {
            searchBtn.disabled = false;
        }
    };

    searchBtn.addEventListener('click', searchSong);
    songNameInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            searchSong();
        }
    });

    window.downloadSong = downloadSong;

    const showSuccess = (message) => {
        const errorDiv = document.getElementById('error');
        errorDiv.textContent = message;
        errorDiv.classList.remove('hidden');
        errorDiv.classList.remove('text-red-500');
        errorDiv.classList.add('text-green-500');
        setTimeout(() => {
            errorDiv.classList.add('hidden');
        }, 3000);
    };

    let audioPlayer = null;
    let isPlaying = false;
    let currentPlayingId = null;
    let loadingStates = new Set();

    const updateButtonState = (id, state) => {
        const button = document.querySelector(`[data-play-id="${id}"]`);
        if (!button) return;

        const icon = button.querySelector('i');
        const text = button.querySelector('span');
        const loadingSpinner = button.querySelector('.loading-spinner');

        switch (state) {
            case 'loading':
                button.disabled = true;
                text.textContent = '加载中';
                if (!loadingSpinner) {
                    const spinner = document.createElement('div');
                    spinner.className = 'loading-spinner animate-spin h-4 w-4 border-2 border-white border-t-transparent rounded-full';
                    button.appendChild(spinner);
                }
                break;
            case 'playing':
                button.disabled = false;
                text.textContent = '暂停';
                icon.className = 'ri-pause-line';
                if (loadingSpinner) loadingSpinner.remove();
                break;
            case 'paused':
                button.disabled = false;
                text.textContent = '播放';
                icon.className = 'ri-play-line';
                if (loadingSpinner) loadingSpinner.remove();
                break;
            case 'error':
                button.disabled = false;
                text.textContent = '重试';
                icon.className = 'ri-play-line';
                if (loadingSpinner) loadingSpinner.remove();
                break;
        }
    };

    const playMusic = async (url, id, duration) => {
        try {
            if (currentPlayingId === id && audioPlayer) {
                if (isPlaying) {
                    audioPlayer.pause();
                    isPlaying = false;
                    updateButtonState(id, 'paused');
                } else {
                    audioPlayer.play();
                    isPlaying = true;
                    updateButtonState(id, 'playing');
                }
                return;
            }

            if (loadingStates.has(id)) return;

            loadingStates.add(id);
            updateButtonState(id, 'loading');

            if (audioPlayer) {
                audioPlayer.pause();
                if (currentPlayingId) {
                    updateButtonState(currentPlayingId, 'paused');
                }
            }

            audioPlayer = new Audio();

            const progressContainer = document.querySelector(`[data-progress-container="${id}"]`);
            if (progressContainer) {
                progressContainer.onclick = (e) => {
                    if (!isDragging && audioPlayer) {
                        const rect = progressContainer.getBoundingClientRect();
                        const percentage = (e.clientX - rect.left) / rect.width;
                        audioPlayer.currentTime = percentage * audioPlayer.duration;
                    }
                };
            }

            audioPlayer.addEventListener('timeupdate', () => {
                if (currentPlayingId === id) {
                    const currentTime = audioPlayer.currentTime;
                    const totalDuration = audioPlayer.duration || duration;
                    updateProgress(id, currentTime, totalDuration);
                }
            });

            audioPlayer.addEventListener('canplay', () => {
                loadingStates.delete(id);
                updateButtonState(id, 'playing');
                audioPlayer.play();
                isPlaying = true;
                currentPlayingId = id;
            });

            audioPlayer.addEventListener('ended', () => {
                isPlaying = false;
                currentPlayingId = null;
                updateButtonState(id, 'paused');
                updateProgress(id, 0, audioPlayer.duration);
            });

            audioPlayer.addEventListener('error', () => {
                loadingStates.delete(id);
                updateButtonState(id, 'error');
                showError('播放失败，请稍后重试');
            });

            audioPlayer.addEventListener('pause', () => {
                if (currentPlayingId === id) {
                    updateButtonState(id, 'paused');
                }
            });

            audioPlayer.addEventListener('play', () => {
                if (currentPlayingId === id) {
                    updateButtonState(id, 'playing');
                }
            });

            audioPlayer.addEventListener('loadedmetadata', () => {
                if (currentPlayingId === id) {
                    console.log(`Audio duration loaded: ${audioPlayer.duration}`);
                    updateProgress(id, 0, audioPlayer.duration);
                }
            });

            audioPlayer.src = `/api/play?url=${encodeURIComponent(url)}`;
            audioPlayer.load();

        } catch (error) {
            loadingStates.delete(id);
            updateButtonState(id, 'error');
            showError('播放失败，请稍后重试');
            console.error('播放错误:', error);
        }
    };

    window.playMusic = playMusic;

    let isDragging = false;
    let currentDraggingId = null;
});