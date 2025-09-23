document.addEventListener("DOMContentLoaded", () => {
  const csrfcookie = () => document.cookie.match(/csrftoken=([^;]+)/)[1];
  const rolesTable = document.getElementById("rolesTable");
  const searchInput = document.getElementById("searchUserInput");
  let currentRoleId = null;
  let fuse = null;

  // Attach actions to each role row
  function attachRow(row) {
    const rid = row.dataset.roleId;

    // Add User button
    row.querySelector(".btnAddUser").onclick = () => {
      currentRoleId = rid;
      const modal = document.getElementById("addUserModal");
      modal.setAttribute("data-role-id", rid);

      fetch(`/admin/roles/${rid}/users/`)
        .then(r => r.json())
        .then(data => {
          document.getElementById("roleUserList").innerHTML = data.users.map(u => `
            <li class="list-group-item d-flex align-items-center">
              <img src="${u.photo_url || '/static/img/default-avatar.png'}" class="user-search-img me-2">
              <span>${u.firstname_eng} ${u.lastname_eng} (${u.emp_no})</span>
            </li>
          `).join('');
          fuse = null;
          document.getElementById("searchArea").style.display = "none";
          new bootstrap.Modal(modal).show();
        });
    };

    // Set Privileges button
    row.querySelector(".btnSetPriv").onclick = () => {
      currentRoleId = rid;

      fetch(`/admin/roles/${rid}/privileges/`)
        .then(res => res.json())
        .then(data => {
          const container = document.getElementById("privModalBody");

          container.innerHTML = data.modules.map((mod, i) => `
            <div class="accordion" id="moduleAccordion${i}">
              <div class="accordion-item">
                <h2 class="accordion-header" id="heading${i}">
                  <button class="accordion-button collapsed" type="button" data-bs-toggle="collapse" data-bs-target="#collapse${i}" aria-expanded="false" aria-controls="collapse${i}">
                    ${mod.mod_name}
                  </button>
                </h2>
                <div id="collapse${i}" class="accordion-collapse collapse" data-bs-parent="#moduleAccordion${i}">
                  <div class="accordion-body">
                    ${mod.subs.map(sub => `
                      <div class="mb-2 border-bottom pb-2">
                        <div class="d-flex align-items-center mb-1">
                          <strong>${sub.sub_name}</strong>
                          <select class="form-select form-select-sm ms-3 w-auto" data-subid="${sub.sub_id}">
                            <option value="ALL" ${sub.scope === "ALL" ? "selected" : ""}>ALL</option>
                            <option value="SELF" ${sub.scope === "SELF" ? "selected" : ""}>SELF</option>
                            <option value="NODE" ${sub.scope === "NODE" ? "selected" : ""}>NODE</option>
                          </select>
                        </div>
                        <div>
                          <label class="me-3"><input type="checkbox" class="priv-check" data-subid="${sub.sub_id}" data-flag="access" ${sub.access ? "checked" : ""}> Access</label>
                          <label class="me-3"><input type="checkbox" class="priv-check" data-subid="${sub.sub_id}" data-flag="view" ${sub.view ? "checked" : ""}> View</label>
                          <label class="me-3"><input type="checkbox" class="priv-check" data-subid="${sub.sub_id}" data-flag="create" ${sub.create ? "checked" : ""}> Create</label>
                          <label class="me-3"><input type="checkbox" class="priv-check" data-subid="${sub.sub_id}" data-flag="edit" ${sub.edit ? "checked" : ""}> Edit</label>
                          <label><input type="checkbox" class="priv-check" data-subid="${sub.sub_id}" data-flag="delete" ${sub.delete ? "checked" : ""}> Delete</label>
                        </div>
                      </div>
                    `).join('')}
                  </div>
                </div>
              </div>
            </div>
          `).join('');

          new bootstrap.Modal(document.getElementById("privModal")).show();

          document.getElementById("savePrivBtn").onclick = () => {
            const privilegeItems = [];

            container.querySelectorAll(".priv-check").forEach(checkbox => {
              const subId = checkbox.dataset.subid;
              let itemObj = privilegeItems.find(i => i.sub_id === subId);
              if (!itemObj) {
                const scopeSelect = container.querySelector(`select[data-subid="${subId}"]`);
                itemObj = {
                  sub_id: subId,
                  scope: scopeSelect.value,
                  access: false,
                  view: false,
                  create: false,
                  edit: false,
                  delete: false
                };
                privilegeItems.push(itemObj);
              }
              itemObj[checkbox.dataset.flag] = checkbox.checked;
            });

            fetch(`/admin/roles/${currentRoleId}/save-privileges/`, {
              method: "POST",
              headers: {
                "Content-Type": "application/json",
                "X-CSRFToken": csrfcookie()
              },
              body: JSON.stringify({ privileges: privilegeItems })
            })
              .then(r => r.json())
              .then(resp => {
                if (resp.status === "success") {
                  alert("Privileges saved successfully!");
                  bootstrap.Modal.getInstance(document.getElementById("privModal")).hide();
                } else {
                  alert("Failed to save privileges.");
                }
              })
              .catch(() => alert("Error saving privileges."));
          };
        });
    };

    // View users + privileges
    row.querySelector(".btnViewUsers")?.addEventListener("click", () => {
      currentRoleId = rid;
      fetch(`/admin/roles/${rid}/users-with-privileges/`)
        .then(res => res.json())
        .then(data => {
          const container = document.getElementById("viewUsersBody");
          if (data.users.length === 0) {
            container.innerHTML = '<p>No users assigned to this role.</p>';
            return;
          }

          container.innerHTML = data.users.map(u => `
            <div class="d-flex align-items-center mb-3 border-bottom pb-2">
              <img src="${u.photo_url || '/static/img/default-avatar.png'}" class="user-search-img me-3" style="width:50px; height:50px; object-fit:cover; border-radius:50%;">
              <div>
                <strong>${u.firstname_eng} ${u.lastname_eng} (${u.emp_no})</strong>
                <div class="mt-1">
                  <span class="badge bg-${u.privileges.access ? 'success' : 'secondary'} me-1">Access</span>
                  <span class="badge bg-${u.privileges.view ? 'success' : 'secondary'} me-1">View</span>
                  <span class="badge bg-${u.privileges.create ? 'success' : 'secondary'} me-1">Create</span>
                  <span class="badge bg-${u.privileges.edit ? 'success' : 'secondary'} me-1">Edit</span>
                  <span class="badge bg-${u.privileges.delete ? 'success' : 'secondary'}">Delete</span>
                </div>
              </div>
            </div>
          `).join('');
          new bootstrap.Modal(document.getElementById("viewUsersModal")).show();
        })
        .catch(() => alert("Failed to load users."));
    });
  }

  document.querySelectorAll("#rolesTable tr").forEach(attachRow);

  // Show Search Area
  document.getElementById("showSearchUser").onclick = () => {
    document.getElementById("searchArea").style.display = "block";
    searchInput.focus();
  };

  // Load search data
  async function loadCandidates() {
    const res = await fetch("/api/search-users/?q=");
    const users = await res.json();
    fuse = new Fuse(users, {
      keys: ["firstname_eng", "lastname_eng", "emp_no"],
      threshold: 0.3,
      distance: 100
    });
  }

  // Run search
  async function runSearch() {
    const term = searchInput.value.trim();
    if (!term) {
      document.getElementById("searchResults").innerHTML = "";
      return;
    }
    if (!fuse) await loadCandidates();
    const results = fuse.search(term);
    const users = results.map(r => r.item);

    document.getElementById("searchResults").innerHTML = users.map(u => `
      <li class="list-group-item d-flex align-items-center">
        <img src="${u.photo_url || '/static/img/default-avatar.png'}" class="user-search-img me-2">
        <span>${u.firstname_eng} ${u.lastname_eng} (${u.emp_no})</span>
        <button class="btn btn-sm btn-primary ms-auto btnAddUserRow" 
          data-uid="${u.user_id}" data-firstname="${u.firstname_eng}" 
          data-lastname="${u.lastname_eng}" data-empno="${u.emp_no}" 
          data-photo="${u.photo_url || '/static/img/default-avatar.png'}">Add</button>
      </li>`).join("");

    // Handle Add button
    document.querySelectorAll(".btnAddUserRow").forEach(btn => {
      btn.onclick = () => {
        const uid = btn.dataset.uid;
        const firstname = btn.dataset.firstname;
        const lastname = btn.dataset.lastname;
        const empno = btn.dataset.empno;
        const photo = btn.dataset.photo;

        fetch(`/admin/roles/${currentRoleId}/add-user/`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": csrfcookie()
          },
          body: JSON.stringify({ user_id: uid })
        })
          .then(r => r.json())
          .then(d => {
            if (d.status === "assigned") {
              document.getElementById("roleUserList").innerHTML += `
                <li class="list-group-item d-flex align-items-center">
                  <img src="${photo}" class="user-search-img me-2">
                  <span>${firstname} ${lastname} (${empno})</span>
                </li>`;
              btn.closest("li").remove();
            }
          });
      };
    });
  }

  function debounce(func, wait) {
    let timeout;
    return function (...args) {
      clearTimeout(timeout);
      timeout = setTimeout(() => func.apply(this, args), wait);
    };
  }

  searchInput.addEventListener("input", debounce(runSearch, 300));
});
