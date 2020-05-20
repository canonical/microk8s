$cert = New-SelfSignedCertificate -Subject "CN=test-signing.microk8s.io" -Type CodeSigning  -CertStoreLocation "Cert:\CurrentUser\My"
$CertPassword = ConvertTo-SecureString -String "Password1234" -Force -AsPlainText
Export-PfxCertificate -Cert "cert:\CurrentUser\My\$($cert.Thumbprint)" -FilePath "test-signing.pfx" -Password $CertPassword
