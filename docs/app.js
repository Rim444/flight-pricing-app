let chart = null;
const $ = id => document.getElementById(id);
const API = "";
function logout(){ localStorage.removeItem("t"); localStorage.removeItem("u"); location.href = "login.html"; }
function checkUserType(){
  const u = $("username").value.trim(); const cf = $("password-confirm"), br = $("btn-register");
  if (u === "admin"){ if(cf) cf.classList.add("hidden"); if(br) br.classList.add("hidden"); }
  else { if(cf) cf.classList.remove("hidden"); if(br) br.classList.remove("hidden"); }
}
async function post(path, body){
  const r = await fetch(API + path, { method:"POST", headers:{"Content-Type":"application/json"}, body: JSON.stringify(body) });
  let d = {}; try { d = await r.json(); } catch(e){} return { ok:r.ok, data:d };
}
async function login(){
  const u = $("username").value.trim(), p = $("password").value;
  $("error-msg").textContent = "Входим... (первый запрос будит сервер, до ~50 сек)";
  try {
    const { ok, data } = await post("/login", { username:u, password:p });
    if (!ok){ $("error-msg").textContent = data.detail || "Ошибка входа"; return; }
    localStorage.setItem("t", data.access_token); localStorage.setItem("u", data.user || u); location.href = "index.html";
  } catch(e){ $("error-msg").textContent = "Сервер не отвечает. Нажми Войти ещё раз."; }
}
async function register(){
  const u = $("username").value.trim(), p = $("password").value, c = $("password-confirm").value;
  if (p !== c){ $("error-msg").textContent = "Пароли не совпадают"; return; }
  $("error-msg").textContent = "Регистрируем...";
  try {
    const { ok, data } = await post("/register", { username:u, password:p });
    $("error-msg").textContent = ok ? "Готово, теперь нажми Войти" : (data.detail || "Ошибка");
  } catch(e){ $("error-msg").textContent = "Сервер не отвечает"; }
}
async function boot(){
  const t = localStorage.getItem("t"); if (!t){ location.href = "login.html"; return; }
  const who = $("who"); if (who) who.textContent = "пользователь: " + (localStorage.getItem("u") || "admin");
  let rs;
  try {
    const r = await fetch(API + "/api/routes", { headers:{ Authorization:"Bearer " + t } });
    if (r.status === 401){ logout(); return; } rs = await r.json();
  } catch(e){ alert("Сервер не отвечает, обнови страницу"); return; }
  const sel = $("route"); sel.innerHTML = ""; const priceMap = {};
  rs.forEach(item => {
    const o = document.createElement("option"); const name = typeof item === "string" ? item : item.route;
    o.value = name; o.textContent = name; sel.appendChild(o);
    if (item && item.base_price != null) priceMap[name] = item.base_price;
  });
  const applyPrice = () => { const bp = priceMap[sel.value]; if (bp != null) $("price").value = Math.round(bp); };
  sel.addEventListener("change", applyPrice); applyPrice();
}
async function calc(){
  const t = localStorage.getItem("t"); if (!t){ logout(); return; }
  const route = $("route").value, date = $("date").value, price = parseFloat($("price").value);
  if (!date || isNaN(price)){ alert("Заполните дату и цену"); return; }
  const url = API + `/api/calculate?route=${encodeURIComponent(route)}&date=${date}&price=${price}`;
  let r;
  try { r = await fetch(url, { headers:{ Authorization:"Bearer " + t } }); }
  catch(e){ alert("Сервер не отвечает, повтори через 10 сек"); return; }
  if (r.status === 401){ alert("Сессия истекла"); logout(); return; }
  if (!r.ok){ let d={}; try{ d = await r.json(); }catch(e){} alert(d.detail || "Нет данных на эту дату"); return; }
  const d = await r.json();
  $("results").classList.remove("hidden"); $("chart-container").classList.remove("hidden");
  $("total-seats").textContent = d.seats; $("want-to-buy").textContent = d.want;
  $("sold").textContent = d.sold; $("remaining").textContent = d.free;
  const cp = $("chart-price"); if (cp) cp.textContent = Math.round(price).toLocaleString("ru-RU");
  const ctx = $("distributionChart").getContext("2d"); if (chart) chart.destroy();
  chart = new Chart(ctx, {
    type: "bar",
    data: { labels: d.labels.map(x => "квантиль " + x), datasets: [
      { label: "Желают купить (чел.)", data: d.quantiles, backgroundColor: "rgba(124,92,255,.55)", borderColor: "#7C5CFF", borderWidth: 1, borderRadius: 6 },
      { label: "Мест в самолёте (" + d.seats + ")", type: "line", data: d.labels.map(() => d.seats), borderColor: "#FFFFFF", borderDash: [6,4], pointRadius: 0, borderWidth: 2, fill: false }
    ]},
    options: { responsive: true,
      plugins: { legend: { labels: { color: "#E8E8EF", font: { family: "Manrope", weight: "700" } } } },
      scales: {
        x: { ticks: { color: "#9A9AA8", font: { family: "Manrope" } }, grid: { color: "rgba(42,42,51,.6)" } },
        y: { beginAtZero: true, ticks: { color: "#9A9AA8", font: { family: "Manrope" } }, grid: { color: "rgba(42,42,51,.6)" },
             title: { display: true, text: "человек", color: "#9A9AA8", font: { family: "Manrope", weight: "700" } } }
      }
    }
  });
}
if ($("route")) boot();