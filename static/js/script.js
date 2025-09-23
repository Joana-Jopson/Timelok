const toggle = document.getElementById('togglePassword');
    const passwordInput = document.getElementById('password');

    toggle.addEventListener('click', () => {
      const type = passwordInput.getAttribute('type') === 'password' ? 'text' : 'password';
      passwordInput.setAttribute('type', type);
      toggle.classList.toggle('fa-eye');
      toggle.classList.toggle('fa-eye-slash');
    });

    function showAddForm() {
    document.getElementById('addForm').style.display = 'block';
    document.getElementById('updateForm').style.display = 'none';
  }

  function showUpdateForm() {
    document.getElementById('addForm').style.display = 'none';
    document.getElementById('updateForm').style.display = 'block';
  }
  $(document).ready(function () {
            $('.custom-file-input').on('change', function () {
                const fileName = $(this).val().split('\\').pop();
                $(this).next('.custom-file-label').html(fileName);
            });
        });

        document.addEventListener('DOMContentLoaded', function() {
            var popupBox = document.getElementById('popup-box');
            if (popupBox) {
                popupBox.style.display = 'block';
                setTimeout(function() {
                    closePopup();
                }, 3000); // Automatically close after 3 seconds
            }
        });
        
        function closePopup() {
            var popupBox = document.getElementById('popup-box');
            if (popupBox) {
                popupBox.style.display = 'none';
            }
        }
  setTimeout(() => {
    document.querySelectorAll('.alert').forEach(el => {
      let alert = bootstrap.Alert.getOrCreateInstance(el);
      alert.close();
    });
  }, 5000);


  document.addEventListener("DOMContentLoaded", function () {
    const searchBar = document.getElementById("search-bar");
    const resultsBox = document.getElementById("search-results");

    searchBar.addEventListener("input", function () {
        const query = this.value.trim();
        if (query.length === 0) {
            resultsBox.innerHTML = "";
            return;
        }

        fetch(`/ajax/employee-search/?q=${query}`)
            .then(response => response.json())
            .then(data => {
                resultsBox.innerHTML = "";
                data.forEach(user => {
                    const div = document.createElement("a");
                    div.classList.add("list-group-item", "list-group-item-action", "d-flex", "align-items-center");
                    div.href = `/chat/${user.employee_id}/`;

                    const img = document.createElement("img");
                    img.src = user.photo || "https://via.placeholder.com/35";
                    img.className = "rounded-circle me-2";
                    img.style.width = "35px";
                    img.style.height = "35px";

                    div.appendChild(img);
                    div.appendChild(document.createTextNode(user.name));
                    resultsBox.appendChild(div);
                });
            });
    });

    document.addEventListener("click", function (e) {
        if (!resultsBox.contains(e.target) && e.target !== searchBar) {
            resultsBox.innerHTML = "";
        }
    });
});

function confirmLogout() {
    if (confirm("Are you sure you want to logout?")) {
        document.getElementById('logoutForm').submit();
    }
}

