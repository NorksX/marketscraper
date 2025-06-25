node {
    def buildNumber = env.BUILD_NUMBER
    echo "Build Number: ${buildNumber}"

    stage('Checkout') {
        checkout scm
    }

    stage('Build & Push it_mk_scraper') {
        // Only run if files in scrapers/it_mk_scraper/ changed
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
    sshagent(['aws-ec2-ssh']) {
        withCredentials([file(credentialsId: '.env_markettracker', variable: 'ENV_FILE')]) {
            sh '''
            scp -o StrictHostKeyChecking=no docker-compose.yml ec2-user@ec2-51-20-9-234.eu-north-1.compute.amazonaws.com:/home/ec2-user/MarketTracker/
            cp $ENV_FILE .env
            scp -o StrictHostKeyChecking=no .env ec2-user@ec2-51-20-9-234.eu-north-1.compute.amazonaws.com:/home/ec2-user/MarketTracker/
            ssh -o StrictHostKeyChecking=no ec2-user@ec2-51-20-9-234.eu-north-1.compute.amazonaws.com '
                cd /home/ec2-user/MarketTracker && \
                docker-compose pull && \
                docker-compose up -d
            '
            '''
        }
    }
}
