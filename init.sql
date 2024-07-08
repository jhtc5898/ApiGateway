-- drop table servicios ;

CREATE TABLE servicio (
    id VARCHAR(255) PRIMARY KEY,
    url VARCHAR(255) NOT NULL,
    nombre VARCHAR(100) NOT NULL,
    estado CHAR(1) NOT NULL DEFAULT '0'
);


INSERT INTO servicio (id,url,nombre,estado) VALUES
	 ('servicio1','http://192.168.88.7:8090','Servicio 1','1'),
	 ('servicio2','http://172.16.26.27:5002','Servicio 2','1'),
	 ('servicio3','http://172.16.26.27:3000','Servicio 3','1'),
     ('servicio4','http://172.16.26.27:5001','Servicio 4','1'),
	 ('servicio5','http://34.88.154.99','Servicio 5','1');


