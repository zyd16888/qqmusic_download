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
                    <button
                        onclick='downloadSong("${song.url}", ${JSON.stringify(song).replace(/'/g, "\\'")});'
                        class="mt-2 px-4 py-2 bg-green-500 text-white rounded-lg hover:bg-green-600 flex items-center gap-2 text-sm"
                    >
                        <i class="ri-download-line"></i>
                        下载
                    </button>
                </div>
            </div>
        `;
        return card;
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

    // 添加成功提示函数
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
});