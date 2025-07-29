let refreshTimer;

function refreshPrices() {
    const refreshIcon = document.getElementById('refresh-icon');
    refreshIcon.classList.add('fa-spin');
    
    fetch('/manual_check')
        .then(response => response.json())
        .then(data => {
            updateStockCards(data);
            refreshIcon.classList.remove('fa-spin');
        })
        .catch(error => {
            console.error('Error fetching stock prices:', error);
            refreshIcon.classList.remove('fa-spin');
        });
}

function updateStockCards(stocks) {
    stocks.forEach(stock => {
        // Update current price
        const currentPriceElement = document.getElementById(`current-${stock.symbol}`);
        if (currentPriceElement) {
            currentPriceElement.textContent = `$${stock.current_price.toFixed(2)}`;
        }
        
        // Update status badge
        const statusElement = document.getElementById(`status-${stock.symbol}`);
        if (statusElement) {
            let statusHtml = '';
            if (stock.status === 'target_reached') {
                statusHtml = '<span class="badge bg-success">Target Reached</span>';
            } else if (stock.status === 'stop_loss') {
                statusHtml = '<span class="badge bg-danger">Stop Loss</span>';
            } else if (stock.status === 'error') {
                statusHtml = '<span class="badge bg-warning">Error</span>';
            } else {
                statusHtml = '<span class="badge bg-info">Monitoring</span>';
            }
            statusElement.innerHTML = statusHtml;
        }
        
        // Update progress bar
        const progressElement = document.getElementById(`progress-${stock.symbol}`);
        if (progressElement) {
            const rangeTotal = stock.target_price - stock.stop_loss;
            const currentPosition = rangeTotal > 0 ? 
                ((stock.current_price - stock.stop_loss) / rangeTotal * 100) : 50;
            
            progressElement.style.width = `${Math.max(0, Math.min(100, currentPosition))}%`;
            
            // Update progress bar color
            progressElement.className = 'progress-bar ';
            if (stock.status === 'target_reached') {
                progressElement.className += 'bg-success';
            } else if (stock.status === 'stop_loss') {
                progressElement.className += 'bg-danger';
            } else {
                progressElement.className += 'bg-info';
            }
        }
        
        // Update timestamp
        const updatedElement = document.getElementById(`updated-${stock.symbol}`);
        if (updatedElement) {
            const now = new Date();
            updatedElement.textContent = now.toLocaleTimeString();
        }
    });
}

// Auto-refresh every 5 minutes
function startAutoRefresh() {
    refreshTimer = setInterval(refreshPrices, 300000); // 5 minutes
}

// Stop auto-refresh
function stopAutoRefresh() {
    if (refreshTimer) {
        clearInterval(refreshTimer);
    }
}
// Nuevo botón que llama a manual_check y actualiza la vista
document.getElementById('manual-check-btn').addEventListener('click', function() {
    const refreshIcon = document.getElementById('refresh-icon');
    refreshIcon.classList.add('fa-spin');

    fetch('/manual_check')
        .then(response => response.json())
        .then(data => {
            updateStockCards(data);  // usa la misma lógica visual que refreshPrices()
            refreshIcon.classList.remove('fa-spin');
        })
        .catch(error => {
            console.error('Error en manual_check:', error);
            refreshIcon.classList.remove('fa-spin');
        });
});

document.addEventListener('DOMContentLoaded', function () {
    startAutoRefresh();

    // Nuevo botón: ejecuta manual_check y actualiza la vista
    const manualCheckBtn = document.getElementById('manual-check-btn');
    if (manualCheckBtn) {
        manualCheckBtn.addEventListener('click', function () {
            const refreshIcon = document.getElementById('refresh-icon');
            refreshIcon.classList.add('fa-spin');

            fetch('/manual_check')
                .then(response => response.json())
                .then(data => {
                    updateStockCards(data);
                    refreshIcon.classList.remove('fa-spin');
                })
                .catch(error => {
                    console.error('Error ejecutando manual_check:', error);
                    refreshIcon.classList.remove('fa-spin');
                });
        });
    }

    // Visibilidad
    document.addEventListener('visibilitychange', function () {
        if (document.hidden) {
            stopAutoRefresh();
        } else {
            startAutoRefresh();
        }
    });
});

// Handle page unload
window.addEventListener('beforeunload', function() {
    stopAutoRefresh();
});
