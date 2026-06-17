def test_create_and_get_account(client):
    # Create Account
    response = client.post("/accounts/", json={
        "name": "Test Savings",
        "bank_name": "HDFC",
        "account_type": "SAVINGS",
        "opening_balance": 5000.00
    })
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Test Savings"
    assert data["current_balance"] == 5000.00
    account_id = data["id"]
    
    # List Accounts
    response = client.get("/accounts/")
    assert response.status_code == 200
    accounts = response.json()
    assert len(accounts) == 1
    assert accounts[0]["id"] == account_id
    
    # Get Specific Account
    response = client.get(f"/accounts/{account_id}")
    assert response.status_code == 200
    assert response.json()["name"] == "Test Savings"
    
    # Update Account
    response = client.put(f"/accounts/{account_id}", json={
        "name": "HDFC Prime",
        "current_balance": 6500.00
    })
    assert response.status_code == 200
    assert response.json()["name"] == "HDFC Prime"
    assert response.json()["current_balance"] == 6500.00

    # Delete Account
    response = client.delete(f"/accounts/{account_id}")
    assert response.status_code == 204
    
    # Verify Deleted
    response = client.get(f"/accounts/{account_id}")
    assert response.status_code == 404
