import requests, sys

def run(username, password):
    base='http://127.0.0.1:8000/api'
    print('logging in', username)
    resp=requests.post(base+'/users/login/', json={'username':username,'password':password})
    print('login status',resp.status_code, resp.text)
    if resp.status_code==200:
        token=resp.json().get('token')
        print('token',token)
        r2=requests.get(base+'/services/dashboard/', headers={'Authorization':f'Token {token}'})
        print('dash status',r2.status_code)
        print('dash text', r2.text[:1000])
    else:
        print('login failed')

if __name__=='__main__':
    if len(sys.argv)>=3:
        run(sys.argv[1], sys.argv[2])
    else:
        print('usage: test_http2.py user pass')
