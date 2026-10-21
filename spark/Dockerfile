# Official Apache Spark image (Spark 3.5, Java 17, Python 3) plus the PostgreSQL JDBC driver.
# To try a newer Spark, change the FROM line and rebuild: docker compose build
FROM apache/spark:3.5.3-python3

USER root
ADD https://repo1.maven.org/maven2/org/postgresql/postgresql/42.7.4/postgresql-42.7.4.jar /opt/spark/jars/postgresql-42.7.4.jar
RUN chmod 644 /opt/spark/jars/postgresql-42.7.4.jar
USER spark

WORKDIR /opt/job
