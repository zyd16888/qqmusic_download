package main

import (
	"encoding/json"
	"flag"
	"fmt"
	"io"
	"net/http"
	"os"
	"path/filepath"
	"strings"
)

// SongResponse 定义API返回的JSON结构
//
type SongResponse struct {
	Code int    `json:"code"`
	Msg  string `json:"msg"`
	Data struct {
		Id       int    `json:"id"`
		Song     string `json:"song"`
		Subtitle string `json:"subtitle"`
		Singer   string `json:"singer"`
		Album    string `json:"album"`
		Pay      string `json:"pay"`
		Time     string `json:"time"`
		Bpm      int    `json:"bpm"`
		Quality  string `json:"quality"`
		Interval string `json:"interval"`
		Size     string `json:"size"`
		Kbps     string `json:"kbps"`
		Cover    string `json:"cover"`
		Link     string `json:"link"`
		Url      string `json:"url"`
	} `json:"data"`
}

func downloadSong(keyword string, n int, q int) error {
	// 创建downloads目录
	if err := os.MkdirAll("downloads", 0755); err != nil {
		return fmt.Errorf("创建下载目录失败: %v", err)
	}

	// 构建API URL
	baseURL := "https://api.lolimi.cn/API/qqdg/"
	url := fmt.Sprintf("%s?word=%s&n=%d&q=%d", baseURL, keyword, n, q)

	// 获取歌曲信息
	resp, err := http.Get(url)
	if err != nil {
		return fmt.Errorf("请求API失败: %v", err)
	}
	defer resp.Body.Close()

	var songResp SongResponse
	if err := json.NewDecoder(resp.Body).Decode(&songResp); err != nil {
		return fmt.Errorf("解析响应失败: %v", err)
	}

	if songResp.Code != 200 {
		return fmt.Errorf("获取歌曲信息失败: %s", songResp.Msg)
	}

	// 确定文件扩展名
	fileExt := ".mp3"
	if strings.Contains(strings.ToLower(songResp.Data.Url), "flac") {
		fileExt = ".flac"
	}

	// 构建文件名
	filename := fmt.Sprintf("%s - %s%s", songResp.Data.Singer, songResp.Data.Song, fileExt)
	filename = sanitizeFilename(filename)
	filepath := filepath.Join("downloads", filename)

	// 下载歌曲
	fmt.Printf("正在下载: %s\n", filename)
	fmt.Printf("音质: %s\n", songResp.Data.Quality)
	fmt.Printf("比特率: %s\n", songResp.Data.Kbps)

	return downloadFile(filepath, songResp.Data.Url)
}

// sanitizeFilename 清理文件名中的非法字符
func sanitizeFilename(filename string) string {
	illegal := []string{"<", ">", ":", "\"", "/", "\\", "|", "?", "*"}
	result := filename
	for _, char := range illegal {
		result = strings.ReplaceAll(result, char, "")
	}
	return result
}

// downloadFile 下载文件到指定路径
func downloadFile(filepath string, url string) error {
	resp, err := http.Get(url)
	if err != nil {
		return fmt.Errorf("下载文件失败: %v", err)
	}
	defer resp.Body.Close()

	out, err := os.Create(filepath)
	if err != nil {
		return fmt.Errorf("创建文件失败: %v", err)
	}
	defer out.Close()

	_, err = io.Copy(out, resp.Body)
	if err != nil {
		return fmt.Errorf("保存文件失败: %v", err)
	}

	fmt.Printf("下载完成！保存在: %s\n", filepath)
	return nil
}

func main() {
	keyword := flag.String("s", "", "要下载的歌曲名称")
	n := flag.Int("n", 1, "搜索结果的序号（可选）")
	q := flag.Int("q", 11, "音质，范围1-14，从差到好（可选）")

	flag.Parse()

	if *keyword == "" {
		fmt.Println("请提供要下载的歌曲名称")
		flag.Usage()
		os.Exit(1)
	}

	if err := downloadSong(*keyword, *n, *q); err != nil {
		fmt.Printf("错误: %v\n", err)
		os.Exit(1)
	}
}
