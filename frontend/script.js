const API_URL = "http://127.0.0.1:5000";

// Save logged-in user info
function saveUser(username, role) {
  localStorage.setItem("username", username);
  localStorage.setItem("role", role);
}

// Get logged-in user info
function getUser() {
  return {
    username: localStorage.getItem("username"),
    role: localStorage.getItem("role")
  };
}

// Logout user
function logout() {
  localStorage.clear();
  window.location.href = "index.html";
}

// -------- LOGIN --------
async function login() {
  const username = document.getElementById("login-username").value.trim();
  const password = document.getElementById("login-password").value.trim();

  if (!username || !password) {
    alert("Please enter both username and password.");
    return;
  }

  try {
    const res = await fetch(`${API_URL}/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password })
    });

    const data = await res.json();

    if (res.ok) {
      saveUser(data.username, data.role);
      if (data.role === "admin") {
        window.location.href = "admin.html";
      } else {
        window.location.href = "user.html";
      }
    } else {
      alert(data.error || "Login failed");
    }
  } catch (err) {
    alert("Server error during login.");
    console.error(err);
  }
}

// -------- SIGNUP --------
async function signup() {
  const username = document.getElementById("signup-username").value.trim();
  const password = document.getElementById("signup-password").value.trim();

  if (!username || !password) {
    alert("Please enter both username and password.");
    return;
  }

  try {
    const res = await fetch(`${API_URL}/signup`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password }) // no role, backend decides
    });

    const data = await res.json();

    if (res.ok) {
      alert(data.message);
      saveUser(username, data.role);

      if (data.role === "admin") {
        window.location.href = "admin.html";
      } else {
        window.location.href = "user.html";
      }
    } else {
      alert(data.error || "Signup failed");
    }
  } catch (err) {
    alert("Server error during signup.");
    console.error(err);
  }
}

// -------- USER DASHBOARD --------
async function loadQuestion() {
  try {
    const res = await fetch(`${API_URL}/get_question`);
    const data = await res.json();

    if (res.ok && data.question) {
      document.getElementById("question").innerText = data.question;
      document.getElementById("question-box").setAttribute("data-qid", data.id);
    } else {
      document.getElementById("question").innerText = "⚠️ No more questions available.";
      document.getElementById("question-box").setAttribute("data-qid", "");
    }
  } catch (err) {
    console.error(err);
    alert("Error fetching question.");
  }
}

// "Next Question" button
function nextQuestion() {
  loadQuestion();
}

window.onload = () => {
  if (document.body.classList.contains("user-page")) {
    const { username } = getUser();
    if (!username) {
      window.location.href = "index.html"; // force login if not logged in
      return;
    }
    document.getElementById("user-name").innerText = username;
    loadQuestion();
  } else if (document.body.classList.contains("admin-page")) {
    const { role } = getUser();
    if (role !== "admin") {
      alert("Unauthorized! Admins only.");
      window.location.href = "index.html";
      return;
    }
    loadUsers();
  }
};

// Submit answer
async function submitAnswer() {
  const { username } = getUser();
  const qid = document.getElementById("question-box").getAttribute("data-qid");
  const answer = document.getElementById("answer").value.trim();

  if (!answer) {
    alert("Please enter your answer.");
    return;
  }
  if (!qid) {
    alert("No question selected.");
    return;
  }

  try {
    const res = await fetch(`${API_URL}/submit_answer`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, question_id: qid, answer })
    });

    const data = await res.json();

    if (res.ok) {
      alert(`Feedback: ${data.feedback}\nConfidence: ${data.confidence}`);
      loadQuestion(); // load next question automatically
      document.getElementById("answer").value = "";
    } else {
      alert(data.error || "Error submitting answer");
    }
  } catch (err) {
    console.error(err);
    alert("Server error while submitting answer.");
  }
}

// Load history
async function loadHistory() {
  const { username } = getUser();

  try {
    const res = await fetch(`${API_URL}/get_history/${username}`);
    const data = await res.json();

    const historyList = document.getElementById("history");
    historyList.innerHTML = "";

    if (res.ok && data.length > 0) {
      data.forEach(item => {
        const li = document.createElement("li");
        li.innerText = `${item.question} → ${item.answer} [${item.feedback}]`;
        historyList.appendChild(li);
      });
    } else {
      const li = document.createElement("li");
      li.innerText = "No history found.";
      historyList.appendChild(li);
    }
  } catch (err) {
    console.error(err);
    alert("Error loading history.");
  }
}

// -------- ADMIN DASHBOARD --------
async function addQuestion() {
  const question = document.getElementById("new-question").value.trim();
  const difficulty = document.getElementById("difficulty").value;

  if (!question) {
    alert("Please enter a question.");
    return;
  }

  try {
    const res = await fetch(`${API_URL}/admin/add_question`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question, difficulty })
    });

    const data = await res.json();
    alert(data.message || data.error);
    document.getElementById("new-question").value = "";
  } catch (err) {
    console.error(err);
    alert("Error adding question.");
  }
}

async function loadUsers() {
  try {
    const res = await fetch(`${API_URL}/admin/get_all_users`);
    const data = await res.json();

    const userList = document.getElementById("user-list");
    userList.innerHTML = "";

    if (res.ok && data.length > 0) {
      data.forEach(user => {
        const li = document.createElement("li");
        li.innerText = `${user.username} (${user.role})`;
        userList.appendChild(li);
      });
    } else {
      const li = document.createElement("li");
      li.innerText = "No users found.";
      userList.appendChild(li);
    }
  } catch (err) {
    console.error(err);
    alert("Error loading users.");
  }
}
