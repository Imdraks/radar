from decimal import Decimal


def test_quote_invoice_payment_lifecycle_and_tenant_isolation(client, db_session, actors, headers):
    for ws in actors[1]:
        ws.plan = 'business'
    db_session.commit()
    def quote_for(index):
        response = client.post('/api/v1/billing/quotes', headers=headers(index), json={
            'title':'Production service','items':[{'description':'Day of production','quantity':'2','unit_price':'100'}]})
        assert response.status_code == 200, response.text
        assert Decimal(response.json()['total']) == Decimal('240')
        return response.json()
    quote = quote_for(0)
    other = quote_for(1)
    assert quote['reference'] == other['reference']  # Tenant numbering is independent.
    assert client.get(f"/api/v1/billing/quotes/{quote['id']}", headers=headers(1)).status_code == 404
    assert client.post(f"/api/v1/billing/quotes/{quote['id']}/accept", headers=headers()).status_code == 200
    converted = client.post(f"/api/v1/billing/quotes/{quote['id']}/convert", headers=headers(), json={})
    assert converted.status_code == 200, converted.text
    invoice = converted.json()
    assert Decimal(invoice['total']) == Decimal('240')
    duplicate = client.post(f"/api/v1/billing/quotes/{quote['id']}/convert", headers=headers(), json={})
    assert duplicate.status_code == 400
    assert client.post(f"/api/v1/billing/invoices/{invoice['id']}/payment", headers=headers(1), json={'amount_paid':'240'}).status_code == 404
    paid = client.post(f"/api/v1/billing/invoices/{invoice['id']}/payment", headers=headers(), json={'amount_paid':'240'})
    assert paid.status_code == 200, paid.text
    assert paid.json()['status'].lower() == 'paid'
    assert client.delete(f"/api/v1/billing/invoices/{invoice['id']}", headers=headers()).status_code == 400


def test_platform_user_management_is_not_an_agency_permission(client, actors, headers):
    assert client.get('/api/v1/users', headers=headers()).status_code == 403
