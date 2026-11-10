const API_URL = "https://flight-pricing-app.de1.netrun.io";
let chartInstance = null;

function logout() {
    localStorage.removeItem("token");
    window.location.href = "login.html";
}

async function login() {
    const username = document.getElementById("username").value;
    const password = document.getElementById("password").value;
    const errorEl = document.getElementById("error-msg");
    errorEl.innerText = "Загрузка...";

    try {
        const response = await fetch(`${API_URL}/login`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ username, password })
        });
        if (response.ok) {
            const data = await response.json();
            localStorage.setItem("token", data.access_token);
            window.location.href = "index.html";
        } else {
            const err = await response.json();
            errorEl.innerText = "Ошибка: " + JSON.stringify(err.detail);
        }
    } catch (e) {
        errorEl.innerText = "Сервер спит. Подождите 30 секунд и нажмите еще раз.";
    }
}

async function register() {
    const username = document.getElementById("username").value;
    const password = document.getElementById("password").value;
    const errorEl = document.getElementById("error-msg");
    
    if (username.length < 3) {
        errorEl.innerText = "Логин должен быть от 3 символов!";
        return;
    }
    if (password.length < 6) {
        errorEl.innerText = "Пароль должен быть от 6 символов!";
        return;
    }
    errorEl.innerText = "Загрузка...";

    try {
        const response = await fetch(`${API_URL}/register`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ username, password })
        });
        if (response.ok) {
            alert("Регистрация успешна! Теперь войдите.");
            errorEl.innerText = "";
        } else {
            const err = await response.json();
            errorEl.innerText = "Сервер: " + JSON.stringify(err.detail);
        }
    } catch (e) {
        errorEl.innerText = "Сервер спит. Подождите 30 секунд.";
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
            alert("Ошибка авторизации.");
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
        alert("Сервер просыпается. Подождите 30 секунд и нажмите еще раз.");
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
            scales: { y: { beginAtZero: true } }
        }
    });
}

if (document.getElementById("route")) {
    if (!localStorage.getItem("token")) {
        window.location.href = "login.html";
    }
}