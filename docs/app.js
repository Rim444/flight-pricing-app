const API_URL = "https://fly3.de1.netrun.io";
let chartInstance = null;

// Эта функция будет автоматически будить сервер при загрузке страницы
async function wakeUpServer() {
    const errorEl = document.getElementById("error-msg");
    if (errorEl) errorEl.innerText = "Подключение к серверу...";
    
    for (let i = 0; i < 10; i++) {
        try {
            const res = await fetch(`${API_URL}/`);
            if (res.ok) {
                if (errorEl) errorEl.innerText = "Сервер готов! Введите данные.";
                return;
            }
        } catch (e) {
            // Игнорируем ошибку, сервер спит
        }
        await new Promise(r => setTimeout(r, 3000));
    }
    if (errorEl) errorEl.innerText = "Сервер не отвечает. Попробуйте обновить страницу.";
}

if (window.location.pathname.endsWith("login.html")) {
    window.onload = wakeUpServer;
}

function logout() {
    localStorage.removeItem("token");
    window.location.href = "login.html";
}

function checkUserType() {
    const username = document.getElementById("username").value;
    const confirmField = document.getElementById("password-confirm");
    const btnReg = document.getElementById("btn-register");
    
    if (username === "admin") {
        confirmField.classList.add("hidden");
        btnReg.classList.add("hidden");
    } else {
        confirmField.classList.remove("hidden");
        btnReg.classList.remove("hidden");
    }
}

async function login() {
    const username = document.getElementById("username").value;
    const password = document.getElementById("password").value;
    const errorEl = document.getElementById("error-msg");
    errorEl.innerText = "Вход...";

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
            errorEl.innerText = "Ошибка: " + err.detail;
        }
    } catch (e) {
        errorEl.innerText = "Ошибка сети. Сервер просыпается, подождите 10 сек и нажмите снова.";
    }
}

async function register() {
    const username = document.getElementById("username").value;
    const password = document.getElementById("password").value;
    const confirm = document.getElementById("password-confirm").value;
    const errorEl = document.getElementById("error-msg");
    
    if (password !== confirm) {
        errorEl.innerText = "Пароли не совпадают!";
        return;
    }
    errorEl.innerText = "Регистрация...";

    try {
        const response = await fetch(`${API_URL}/register`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ username, password })
        });
        
        if (response.ok) {
            alert("Регистрация успешна! Теперь нажмите Войти.");
            errorEl.innerText = "";
        } else {
            const err = await response.json();
            errorEl.innerText = "Сервер: " + err.detail;
        }
    } catch (e) {
        errorEl.innerText = "Ошибка сети. Подождите 10 сек.";
    }
}

async function calculate() {
    const token = localStorage.getItem("token");
    if (!token) { window.location.href = "login.html"; return; }

    const route = document.getElementById("route").value;
    const date = document.getElementById("date").value;
    const price = document.getElementById("price").value;
    if (!date || !price) { alert("Заполните дату и цену"); return; }

    try {
        const response = await fetch(`${API_URL}/api/calculate?route=${route}&date=${date}&price=${price}`, {
            method: "GET",
            headers: { "Authorization": `Bearer ${token}` }
        });
        
        if (response.status === 401) { alert("Ошибка входа"); logout(); return; }
        if (!response.ok) { alert("Данные не найдены"); return; }

        const data = await response.json();
        document.getElementById("results").classList.remove("hidden");
        document.getElementById("chart-container").classList.remove("hidden");
        document.getElementById("total-seats").innerText = data.total_seats;
        document.getElementById("want-to-buy").innerText = data.want_to_buy;
        document.getElementById("sold").innerText = data.sold;
        document.getElementById("remaining").innerText = data.remaining;

        const ctx = document.getElementById('distributionChart').getContext('2d');
        if (window.chartInstance) window.chartInstance.destroy();
        window.chartInstance = new Chart(ctx, {
            type: 'line',
            data: {
                labels: ['10%', '20%', '30%', '40%', '50%', '60%', '70%', '80%', '90%'],
                datasets: [
                    { label: 'Спрос', data: data.quantiles, borderColor: '#3b82f6', backgroundColor: 'rgba(59, 130, 246, 0.2)', fill: true },
                    { label: 'Места', data: new Array(9).fill(data.total_seats), borderColor: '#ef4444', borderDash: [5, 5] }
                ]
            }
        });
    } catch (e) { alert("Сервер просыпается... Нажмите Рассчитать еще раз через 10 секунд."); }
}

if (document.getElementById("route")) {
    if (!localStorage.getItem("token")) { window.location.href = "login.html"; }
}