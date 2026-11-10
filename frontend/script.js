const API_URL = "https://flight-pricing-app.de1.netrun.io";
let chartInstance = null;

function logout() {
    localStorage.removeItem("token");
    window.location.href = "login.html";
}

async function login() {
    const username = document.getElementById("username").value;
    const password = document.getElementById("password").value;
    const formData = new URLSearchParams();
    formData.append("username", username);
    formData.append("password", password);

    try {
        const response = await fetch(`${API_URL}/token`, {
            method: "POST",
            headers: { "Content-Type": "application/x-www-form-urlencoded" },
            body: formData
        });
        if (response.ok) {
            const data = await response.json();
            localStorage.setItem("token", data.access_token);
            window.location.href = "index.html";
        } else {
            document.getElementById("error-msg").innerText = "Неверный логин или пароль";
        }
    } catch (e) {
        document.getElementById("error-msg").innerText = "Ошибка подключения к серверу";
    }
}

async function register() {
    const username = document.getElementById("username").value;
    const password = document.getElementById("password").value;
    const formData = new URLSearchParams();
    formData.append("username", username);
    formData.append("password", password);

    try {
        const response = await fetch(`${API_URL}/register`, {
            method: "POST",
            headers: { "Content-Type": "application/x-www-form-urlencoded" },
            body: formData
        });
        if (response.ok) {
            alert("Регистрация успешна! Теперь войдите.");
        } else {
            document.getElementById("error-msg").innerText = "Пользователь уже существует";
        }
    } catch (e) {
        document.getElementById("error-msg").innerText = "Ошибка подключения к серверу";
    }
}

async function calculate() {
    const token = localStorage.getItem("token");
    if (!token) {
        window.location.href = "login.html";
        return;
    }

    const route = document.getElementById("route").value;
    const date = document.getElementById("date").value;
    const price = document.getElementById("price").value;

    if (!date || !price) {
        alert("Заполните дату и цену");
        return;
    }

    try {
        const response = await fetch(`${API_URL}/api/calculate?route=${route}&date=${date}&price=${price}`, {
            method: "GET",
            headers: { "Authorization": `Bearer ${token}` }
        });
        
        if (response.status === 401) {
            logout();
            return;
        }
        
        if (!response.ok) {
            alert("Ошибка: маршрут или дата не найдены в прогнозе");
            return;
        }

        const data = await response.json();
        
        document.getElementById("results").classList.remove("hidden");
        document.getElementById("chart-container").classList.remove("hidden");
        
        document.getElementById("total-seats").innerText = data.total_seats;
        document.getElementById("want-to-buy").innerText = data.want_to_buy;
        document.getElementById("sold").innerText = data.sold;
        document.getElementById("remaining").innerText = data.remaining;

        drawChart(data.quantiles, data.total_seats);
    } catch (e) {
        alert("Ошибка подключения к серверу");
    }
}

function drawChart(quantiles, seats) {
    const ctx = document.getElementById('distributionChart').getContext('2d');
    const labels = ['10%', '20%', '30%', '40%', '50% (Медиана)', '60%', '70%', '80%', '90%'];
    const seatsLine = new Array(9).fill(seats);

    if (chartInstance) {
        chartInstance.destroy();
    }

    chartInstance = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [
                {
                    label: 'Прогноз спроса',
                    data: quantiles,
                    borderColor: '#3b82f6',
                    backgroundColor: 'rgba(59, 130, 246, 0.2)',
                    fill: true,
                    tension: 0.4,
                    pointRadius: 4
                },
                {
                    label: 'Всего мест (вместимость)',
                    data: seatsLine,
                    borderColor: '#ef4444',
                    borderDash: [5, 5],
                    pointRadius: 0,
                    fill: false
                }
            ]
        },
        options: {
            responsive: true,
            scales: {
                y: { beginAtZero: true }
            }
        }
    });
}

if (window.location.pathname.endsWith("index.html")) {
    if (!localStorage.getItem("token")) {
        window.location.href = "login.html";
    }
}