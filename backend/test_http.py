import requests
import sys


def run():
    print('=== starting test_http.py ===')

    base = 'http://127.0.0.1:8000/api'
    creds = {'username': 'testuser2', 'password': 'ClientPassword123!'}
    print('logging in')
    try:
        resp = requests.post(base + '/users/login/', json=creds, timeout=10)
        print('login status', resp.status_code, resp.text)
        if resp.status_code == 200:
            token = resp.json().get('token')
            print('token', token)
            r2 = requests.get(
                base + '/services/dashboard/',
                headers={'Authorization': f'Token {token}'},
                timeout=10,
            )
            print('dash status', r2.status_code)
            print('dash text', r2.text[:1000])
        else:
            print('login failed')
    except Exception as e:
        print('exception', e, file=sys.stderr)


if __name__ == '__main__':
    run()
