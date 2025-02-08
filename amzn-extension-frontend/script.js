
//---------------------- Results Integrated Code--------------------

document.addEventListener('DOMContentLoaded', function () {

    // Determine which page to load based on the state
    if (localStorage.getItem('login') === 'true') {
        loadPage('iprisk.html');
    } else if (localStorage.getItem('page2') === 'true') {
        loadPage('login.html');
    } else if (localStorage.getItem('page1') === 'true') {
        loadPage('page2.html');
    } else {
        loadPage('page1.html');
    }

    document.addEventListener('click', function (e) {
        if (e.target && e.target.id === 'formLinkButton') {
            loadPage('page2.html');
            localStorage.setItem('page1', 'true');
        } else if (e.target && e.target.id === 'submitButton') {
            const formLinkInput = document.getElementById('formLinkInput').value;
            if (formLinkInput.includes('responded') || formLinkInput.includes('alreadyresponded')) {
                loadPage('login.html');
                localStorage.setItem('page2', 'true');
            } else {
                document.getElementById('errorMessage').style.display = 'block';
            }
        } else if (e.target && e.target.id === 'signUpLink') {
            loadPage('signup.html');
        } else if (e.target && e.target.id === 'loginLink') {
            loadPage('login.html');
        } else if (e.target && e.target.id === 'loginButton') {
            // Handle login logic here
            const email = document.getElementById('email').value;
            const password = document.getElementById('password').value;
            // Assume a local API call to validate the credentials
            if (email === 'user@gmail.com' && password === 'user123') {
                loadPage('iprisk.html');
                localStorage.setItem('login', 'true');
            } else {
                document.getElementById('loginErrorMessage').style.display = 'block';
            }
        } else if (e.target && e.target.id === 'signUpButton') {
            // Handle sign-up logic here
            const email = document.getElementById('signUpEmail').value;
            const password = document.getElementById('signUpPassword').value;
            // Assume a local API call to create the account
            if (email && password) {
                loadPage('login.html');
            } else {
                document.getElementById('signUpErrorMessage').style.display = 'block';
            }
        } else if (e.target && e.target.id === 'checkIpRiskButton') {
            const loader = document.getElementById('loader');
            loader.style.display = 'flex';

            // Extract ASIN from the current tab's URL
            chrome.tabs.query({ active: true, currentWindow: true }, function (tabs) {
                const tab = tabs[0];
                const url = new URL(tab.url);
                const asin = url.pathname.split('/dp/')[1].split('/')[0];

                // Make a POST request to the API with the extracted ASIN
                fetch('http://127.0.0.1:5000/detect_ip_risk', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({ asin: asin })
                })
                .then(response => response.json())
                .then(data => {
                    console.log('data: ', data);
                    loader.style.display = 'none';
                    document.getElementById('pattern_one').textContent = data.pattern_one == 'true'? 'Detected' : 'Not Detected' ;
                    document.getElementById('pattern_two').textContent = data.pattern_two == 'true'? 'Detected' : 'Not Detected';

                    const tableBody1 = document.querySelector('#riskTable1 tbody');
                    tableBody1.innerHTML = '';
                    data.pattern_one_dates.forEach(factor => {
                        const row = `
                            <tr>
                                <td>${factor.start_date}</td>
                                <td>${factor.end_date}</td>

                            </tr>
                        `;
                        tableBody1.innerHTML += row;
                    });


                    const tableBody2 = document.querySelector('#riskTable2 tbody');
                    tableBody2.innerHTML = '';
                    data.pattern_two_dates.forEach(factor => {
                        const row = `
                            <tr>
                                <td>${factor.start_date}</td>
                                <td>${factor.end_date}</td>
                                <td>${factor.dropped_from}</td>
                                <td>${factor.dropped_to}</td>
                            </tr>
                        `;
                        tableBody2.innerHTML += row;
                    });
                })
                .catch(error => {
                    loader.style.display = 'none';
                    console.error('Error:', error);
                });
            });
        } else if (e.target && e.target.id === 'exportCsvButton1') {
            const tableBody = document.querySelector('#riskTable1 tbody');
            const rows = tableBody.querySelectorAll('tr');
            const data = [['Start Date', 'End Date']];
            
            rows.forEach(row => {
                const cells = row.querySelectorAll('td');
                const rowData = Array.from(cells).map(cell => cell.textContent);
                data.push(rowData);
            });
            
            const csvContent = data.map(e => e.join(",")).join("\n");
            const blob = new Blob([csvContent], { type: 'text/csv' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = 'pattern1_dates.csv';
            a.click();
            URL.revokeObjectURL(url);
        } else if (e.target && e.target.id === 'exportCsvButton2') {
            const tableBody = document.querySelector('#riskTable2 tbody');
            const rows = tableBody.querySelectorAll('tr');
            const data = [['Start Date', 'End Date', 'dropped_from', 'dropped_to']];
            
            rows.forEach(row => {
                const cells = row.querySelectorAll('td');
                const rowData = Array.from(cells).map(cell => cell.textContent);
                data.push(rowData);
            });
            
            const csvContent = data.map(e => e.join(",")).join("\n");
            const blob = new Blob([csvContent], { type: 'text/csv' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = 'pattern2_dates.csv';
            a.click();
            URL.revokeObjectURL(url);
        } else if (e.target && e.target.id === 'logoutButton') {
            // Handle logout logic here
            loadPage('login.html');
            localStorage.setItem('login', 'false');
        }
    });

    function loadPage(page) {
        fetch(`pages/${page}`)
            .then(response => response.text())
            .then(html => {
                document.getElementById('content').innerHTML = html;
            })
            .catch(error => {
                console.error('Error loading page:', error);
            });
    }
});