-- drop table servicios ;

CREATE TABLE servicio (
    id VARCHAR(255) PRIMARY KEY,
    url VARCHAR(255) NOT NULL,
    nombre VARCHAR(100) NOT NULL,
    estado CHAR(1) NOT NULL DEFAULT '0'
);


INSERT INTO servicio (id,url,nombre,estado) VALUES
	 ('servicio1','http://192.168.88.5:8090','Servicio 1','1'),
	 ('servicio2','http://192.168.88.5:8090','Servicio 2','1'),
	 ('servicio3','http://192.168.88.5:8090','Servicio 3','1');
