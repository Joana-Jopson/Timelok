document.addEventListener("DOMContentLoaded", function () {
  const parseLabels = data => data.map(item => item.attendance_date || item.hour || item.name);
  const parseData = data => data.map(item => item.count);

  const renderChart = (id, labels, data, type = 'bar') => {
    const ctx = document.getElementById(id);
    if (!ctx) return;
    new Chart(ctx, {
      type: type,
      data: {
        labels: labels,
        datasets: [{
          label: '',
          data: data,
          backgroundColor: 'rgba(54, 162, 235, 0.7)',
          borderColor: 'rgba(54, 162, 235, 1)',
          borderWidth: 1
        }]
      },
      options: {
        responsive: true,
        plugins: { legend: { display: false } },
        scales: { y: { beginAtZero: true } }
      }
    });
  };

  renderChart("attendanceChart", parseLabels(window.trendData), parseData(window.trendData));
  renderChart("deptChart", parseLabels(window.deptData), parseData(window.deptData), 'bar');
  renderChart("designationChart", parseLabels(window.designationData), parseData(window.designationData), 'doughnut');
  renderChart("punchChart", parseLabels(window.punchData), parseData(window.punchData), 'bar');
  renderChart("contractorChart", parseLabels(window.contractorData), parseData(window.contractorData), 'bar');
});