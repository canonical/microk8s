#!/usr/bin/env bash
# 1. Creates a root and intermediate certificate 
# 2. Signs the intermediate certificate
# 3. Creates a folder $CERT_FOLDER/microk8s-certs that contains the certificate/chain/key in the format that microk8s expects.

export CERT_FOLDER=$HOME/certs
export ROOT_CA_FOLDER=$CERT_FOLDER/root/ca
export INTERMEDIATE_CA_FOLDER=$ROOT_CA_FOLDER/intermediate


### Create root CA
mkdir -p "$ROOT_CA_FOLDER"
cd "$ROOT_CA_FOLDER"
mkdir certs crl newcerts private
chmod 700 private
touch index.txt
echo 1000 > serial

echo "Create root openssl config"
sed -i "s#\$ROOT_CA_FOLDER#$ROOT_CA_FOLDER#g" ~/root-openssl-template.cnf
cp ~/root-openssl-template.cnf $ROOT_CA_FOLDER/openssl.cnf

echo "Create root certificate and key"
openssl req -config openssl.cnf -nodes -new -x509  -keyout private/ca.key.pem -out certs/ca.cert.pem -days 7300 -sha256

echo "Create intermediate CA folder"
mkdir $INTERMEDIATE_CA_FOLDER 

echo "Create directory structure"
cd $INTERMEDIATE_CA_FOLDER 
mkdir certs crl csr newcerts private
chmod 700 private
touch index.txt
echo 1000 > serial
echo 1000 > $ROOT_CA_FOLDER/intermediate/crlnumber

echo "Create intermediate openssl config"
sed -i "s#\$INTERMEDIATE_CA_FOLDER#$INTERMEDIATE_CA_FOLDER#g" ~/intermediate-openssl-template.cnf
cp ~/intermediate-openssl-template.cnf $INTERMEDIATE_CA_FOLDER/openssl.cnf

echo "Create intermediate certificate and key"
openssl req -config $INTERMEDIATE_CA_FOLDER/openssl.cnf -nodes -new -sha256 -keyout $INTERMEDIATE_CA_FOLDER/private/intermediate.key.pem -out $INTERMEDIATE_CA_FOLDER/csr/intermediate.csr.pem

echo "Sign intermediate certificate"
openssl ca -config $ROOT_CA_FOLDER/openssl.cnf -extensions v3_intermediate_ca \
   -days 3650 -notext -md sha256 -in $INTERMEDIATE_CA_FOLDER/csr/intermediate.csr.pem \
   -out $INTERMEDIATE_CA_FOLDER/certs/intermediate.cert.pem -batch

echo "Create CA chain file"
cat $ROOT_CA_FOLDER/intermediate/certs/intermediate.cert.pem $ROOT_CA_FOLDER/certs/ca.cert.pem > $ROOT_CA_FOLDER/intermediate/certs/ca-chain.cert.pem

echo "Copy certs over to use for microk8s"
mkdir $CERT_FOLDER/microk8s-certs
cp $INTERMEDIATE_CA_FOLDER/private/intermediate.key.pem $CERT_FOLDER/microk8s-certs/ca.key
cp $INTERMEDIATE_CA_FOLDER/certs/intermediate.cert.pem $CERT_FOLDER/microk8s-certs/ca.crt
cp $INTERMEDIATE_CA_FOLDER/certs/ca-chain.cert.pem $CERT_FOLDER/microk8s-certs/ca-chain.crt




