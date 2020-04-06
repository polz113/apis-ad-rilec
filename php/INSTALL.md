# Namestitev PHP + nginx

Vir: [Prvi zadetek na duckduckgo](https://www.digitalocean.com/community/tutorials/how-to-install-linux-nginx-mysql-php-lemp-stack-in-ubuntu-16-04).

## Namestitev paketov

Za namestitev nginx glej en nivo više.

Potem namestimo php-fpm in [composer](https://getcomposer.org):
```
apt install composer php-fpm
```

## Nastavitev nginx

V privzetih nastavitvah nginx odkomentiramo vrstice pod "pass PHP scripts to FastCGI server" ter "deny access to .htaccess files".

Primer celotne nastavitvene datoteke je v nginx/apis-rilec-php
