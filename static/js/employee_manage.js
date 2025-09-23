$(document).ready(function () {

    // Handle Edit button click
    $('.edit-btn').click(function () {
        const empId = $(this).data('id');

        // ✅ Correctly interpolate empId in the URL
        $.ajax({
            url: `/employees/modal/${empId}/`,
            method: 'GET',
            success: function (response) {
                $('#updateModalBody').html(response);
                $('#updateForm').attr('action', `/employees/update/${empId}/`);
                $('#updateModal').modal('show');
            },
            error: function () {
                alert('Failed to load employee data. Please try again.');
            }
        });
    });

    // Handle Delete button click
    $('.delete-btn').click(function () {
        const empId = $(this).data('id');
        if (confirm('Are you sure you want to deactivate this employee?')) {
            window.location.href = `/employees/delete/${empId}/`;
        }
    });

});
