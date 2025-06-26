node {
    def buildNumber = env.BUILD_NUMBER
    echo "Build Number: ${buildNumber}"

    stage('Checkout') {
        checkout scm
    }

    stage('Build & Push it_mk_scraper') {
        if (currentBuild.changeSets.any { changeSet ->
                changeSet.items.any { item ->
                    item.affectedFiles.any { file ->
                        file.path.startsWith("scrapers/it_mk_scraper/")
                    }
                }
            }) {
            def imageName = "borismanev/it_mk_scraper"
            docker.withRegistry('https://registry.hub.docker.com', 'dockerhub') {
                def img = docker.build("${imageName}:${buildNumber}", "-f scrapers/it_mk_scraper/Dockerfile scrapers/it_mk_scraper")
                img.push(buildNumber)
                img.push('latest')
            }
        }
    }

    stage('Build & Push pazar3_scraper') {
        if (currentBuild.changeSets.any { changeSet ->
                changeSet.items.any { item ->
                    item.affectedFiles.any { file ->
                        file.path.startsWith("scrapers/pazar3_scraper/")
                    }
                }
            }) {
            def imageName = "borismanev/pazar3_scraper"
            docker.withRegistry('https://registry.hub.docker.com', 'dockerhub') {
                def img = docker.build("${imageName}:${buildNumber}", "-f scrapers/pazar3_scraper/Dockerfile scrapers/pazar3_scraper")
                img.push(buildNumber)
                img.push('latest')
            }
        }
    }

    stage('Build & Push reklama5_scraper') {
        if (currentBuild.changeSets.any { changeSet ->
                changeSet.items.any { item ->
                    item.affectedFiles.any { file ->
                        file.path.startsWith("scrapers/reklama5_scraper/")
                    }
                }
            }) {
            def imageName = "borismanev/reklama5_scraper"
            docker.withRegistry('https://registry.hub.docker.com', 'dockerhub') {
                def img = docker.build("${imageName}:${buildNumber}", "-f scrapers/reklama5_scraper/Dockerfile scrapers/reklama5_scraper")
                img.push(buildNumber)
                img.push('latest')
            }
        }
    }

    stage('Build & Push Web') {
        if (currentBuild.changeSets.any { changeSet ->
                changeSet.items.any { item ->
                    item.affectedFiles.any { file ->
                        file.path.startsWith("Web/")
                    }
                }
            }) {
            def imageName = "borismanev/marketscraper_web"
            docker.withRegistry('https://registry.hub.docker.com', 'dockerhub') {
                def img = docker.build("${imageName}:${buildNumber}", "-f Web/Dockerfile Web")
                img.push(buildNumber)
                img.push('latest')
            }
        }
    }

    stage('Deploy to AWS EC2') {
        // Only deploy if docker-compose.yml changed
        if (currentBuild.changeSets.any { changeSet ->
                changeSet.items.any { item ->
                    item.affectedFiles.any { file ->
                        file.path == "docker-compose.yml"
                    }
                }
            }) {
            sshagent(['aws-ec2-ssh']) {
                sh '''
                    ssh -o StrictHostKeyChecking=no ec2-user@ec2-51-20-9-234.eu-north-1.compute.amazonaws.com '
                        cd /home/ec2-user/MarketTracker && \
                        docker compose pull && \
                        docker compose up -d
                    '
                '''
            }
        } else {
            echo "No changes in docker-compose.yml, skipping deployment."
        }
    }
}
