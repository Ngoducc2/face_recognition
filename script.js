// Khởi tạo cấu trúc biểu đồ Chart.js
const ctx = document.getElementById('performanceChart').getContext('2d');
const maxDataPoints = 30; // Giữ lại 30 điểm dữ liệu gần nhất trên biểu đồ

const performanceChart = new Chart(ctx, {
    type: 'line',
    data: {
        labels: Array(maxDataPoints).fill(''),
        datasets: [
            {
                label: 'Tốc độ (FPS)',
                data: Array(maxDataPoints).fill(0),
                borderColor: '#34a853',
                backgroundColor: 'rgba(52, 168, 83, 0.1)',
                borderWidth: 2,
                yAxisID: 'y-fps',
                tension: 0.3
            },
            {
                label: 'Độ trễ AI Inference (ms)',
                data: Array(maxDataPoints).fill(0),
                borderColor: '#ea4335',
                backgroundColor: 'rgba(234, 67, 53, 0.1)',
                borderWidth: 2,
                yAxisID: 'y-ms',
                tension: 0.3
            }
        ]
    },
    options: {
        responsive: true,
        maintainAspectRatio: false,
        scales: {
            'y-fps': {
                type: 'linear',
                position: 'left',
                title: { display: true, text: 'Frames Per Second (FPS)' },
                min: 0,
                max: 60
            },
            'y-ms': {
                type: 'linear',
                position: 'right',
                title: { display: true, text: 'Thời gian xử lý (ms)' },
                min: 0,
                grid: { drawOnChartArea: false } // Tránh trùng lặp lưới đồ thị
            }
        }
    }
});

// Hàm liên tục gọi API để lấy dữ liệu mới (Polling mỗi 300ms)
async function updateDashboard() {
    try {
        const response = await fetch('/api/stats');
        const data = await response.json();
        
        // 1. Cập nhật các ô số liệu nhanh
        document.getElementById('val-fps').innerText = data.fps;
        document.getElementById('val-faces').innerText = data.face_count;
        document.getElementById('val-inference').innerText = data.inference_time > 0 ? data.inference_time + ' ms' : 'Skipped';
        document.getElementById('val-match').innerText = data.matching_time + ' ms';
        
        // 2. Cập nhật biểu đồ đường
        performanceChart.data.datasets[0].data.push(data.fps);
        
        // Chỉ lấy thông số AI khi có tính toán thực tế (>0) để tránh đồ thị bị kéo về 0 ở frame skip
        if(data.inference_time > 0) {
            performanceChart.data.datasets[1].data.push(data.inference_time);
        } else {
            // Giữ lại giá trị cũ nếu frame đó bị skip
            const lastVal = performanceChart.data.datasets[1].data[performanceChart.data.datasets[1].data.length - 1];
            performanceChart.data.datasets[1].data.push(lastVal);
        }
        
        // Xóa bớt điểm dữ liệu cũ vượt quá giới hạn hiển thị
        performanceChart.data.datasets[0].data.shift();
        performanceChart.data.datasets[1].data.shift();
        
        // Cập nhật lại giao diện đồ thị
        performanceChart.update('none'); // Cấu hình 'none' để update mượt mà, không giật hình
        
    } catch (error) {
        console.error("Lỗi khi đồng bộ dữ liệu thống kê:", error);
    }
}

// Cứ mỗi 300ms thì cập nhật dữ liệu một lần
setInterval(updateDashboard, 300);