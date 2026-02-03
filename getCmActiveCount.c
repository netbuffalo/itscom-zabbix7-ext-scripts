/**
 * - Build
 *   $ gcc -o getCmActiveCount getCmActiveCount.c
**/
#include <stdio.h>
#include <ctype.h>
#include <stdlib.h>
#include <unistd.h>
#include <libgen.h>
#include <string.h>
#include <arpa/inet.h>
#include <sys/socket.h>

int search(char str[], char c){
	int i;
	int num = 0;
	
	for(i=0; str[i] != 0; i++){
		if(i >= 256) return -1;
		if(str[i] == c){
			num++;
		}
	}
	return num;
}

int main(int argc, char* argv[]) {
    int ver = 0;
    const char *VERSION = "1.0.0";
    char *DEFAULT_HOST = "127.0.0.1";
    char *DEFAULT_PORT = "9091";

    char *server  = NULL;
    char *port  = NULL;
    char *hostname  = NULL;
    char *pairdatas = NULL;
    char *mdifindex = NULL;
    char *mode = NULL;
    char *tcsid = NULL;

	const char *delim = ",";
	int api_port = 9091;

    int c;
    opterr = 0;

    while ((c = getopt (argc, argv, "s:p:m:d:h:v:t:")) != -1)
      switch (c)
        {
        case 't':
            break;
        case 's':
            server = optarg;
            break;
        case 'p':
            port = optarg;
            break;
        case 'h':
            hostname = optarg;
            break;
        case 'd':
            pairdatas = optarg;
            break;
        case 'm':
            mode = optarg;
            break;
        case 'v':
            ver = 1;
            break;
        case '?':
            if (optopt == 'h')
                fprintf (stderr, "option -%c requires an argument.\n", optopt);
            else if (optopt == 't')
                fprintf (stderr, "option -%c requires an argument.\n", optopt);
            else if (optopt == 's')
                fprintf (stderr, "option -%c requires an argument.\n", optopt);
            else if (optopt == 'p')
                fprintf (stderr, "option -%c requires an argument.\n", optopt);
            else if (optopt == 'd')
                fprintf (stderr, "option -%c requires an argument.\n", optopt);
            else if (optopt == 'm')
                fprintf (stderr, "option -%c requires an argument.\n", optopt);
            else if (isprint(optopt))
                fprintf (stderr, "unknown option `-%c'.\n", optopt);
            else
                fprintf (stderr, "unknown option character `\\x%x'.\n", optopt);
            return 1;
        default:
          abort();
        }

    if (ver) {
        fprintf(stdout, "%s\n", VERSION);
        return 0;
    }

    if (!server) {
		server = DEFAULT_HOST;
    }
    
    if (!port) {
		port = DEFAULT_PORT;
    }
   	// check port is numeric
   	char buf[64];
	int iResult = 0;
   	iResult = sscanf(port, "%d", &api_port);
   	if (EOF == iResult) {
        fprintf(stderr, "option p (port) is numeric value. nothing to do.\n");
        return 1;
	}
   	if (0 == iResult) {
        fprintf(stderr, "option p (port) is numeric value. nothing to do.\n");
   	    return 1;
	}
	
    if (!hostname) {
        fprintf(stderr, "option h (hostname) is required. nothing to do.\n");
        return 1;
    }
   	strcat(hostname, "\n");

    if (!pairdatas) {
        fprintf(stderr, "option d (mdifindex:tcsid,...) is required. nothing to do.\n");
        return 1;
    }

    struct sockaddr_in server_address;
    memset(&server_address, 0, sizeof(server_address));
    server_address.sin_family = AF_INET;

    inet_pton(AF_INET, server, &server_address.sin_addr);

    server_address.sin_port = htons(api_port);

    // open a stream socket
    int sock;
    if ((sock = socket(PF_INET, SOCK_STREAM, 0)) < 0) {
        printf("couldn't create socket.\n");
        return 1;
    }

    // connect to server socket
    if (connect(sock, (struct sockaddr*)&server_address, sizeof(server_address)) < 0) {
        printf("couldn't connect to server.\n");
        return 1;
    }

    // Disassembly mdifindex:tcsid,mdifindex:tcsid,...
   	char *mtcsid_temp;
   	char mtcsid[256];
	char *pcret;
	if ((pcret = strstr(pairdatas, ",")) != NULL) {
		mtcsid_temp = strtok(pairdatas, delim);
	}
	else {
		mtcsid_temp = pairdatas;
	}
	if (mode) {
		strcpy(mtcsid, mode);
		strcat(mtcsid, ":");
		strcat(mtcsid, mtcsid_temp);
		strcat(mtcsid, "\n");
	}
	else {
		strcpy(mtcsid, mtcsid_temp);
		strcat(mtcsid, "\n");
	}
	
	int sum = 0;
	int length = 0;
	int countActive = 0;
	do {
		// for debug
        // printf("mtcsid:%s.\n", mtcsid);
		if (strlen(mtcsid) > 256) {
		    close(sock);
	        printf("(mdifindex:tcsid) length over 256.\n");
    	    return 1;
		}
		char modeString[128];
		memset(modeString, 0, sizeof(modeString));
		int d1,d2;
		d1 = d2 = 0;
		int converted;
		int nColon = search(mtcsid, ':');
		
		if (nColon == 1) {
			converted = sscanf(mtcsid,"%d:%d",&d1,&d2);
			if(converted != 2) {
				close(sock);
				printf("format error (mdifindex:tcsid) .\n");
				return 1;
			}
		}
		else if (nColon == 2) {
			converted = sscanf(mtcsid,"%[^:]:%d:%d", modeString, &d1, &d2);
			if(converted != 3) {
				close(sock);
				printf("format error (mdifindex:tcsid) .\n");
				return 1;
			}
		}
		else {
			close(sock);
			printf("format error (mdifindex:tcsid) .\n");
			return 1;
		}
		
		if((d1 + d2) != 0) {
			// send hostname
			send(sock, hostname, strlen(hostname), 0);

			send(sock, mtcsid, strlen(mtcsid), 0);

			// receive max 64 bytes data
			memset(buf, 0, sizeof(buf));
			length = read(sock, buf, sizeof(buf));

			// check received data
			iResult = sscanf(buf, "%d", &countActive);
			if (EOF == iResult) {
				close(sock);
				printf("invalid data received.\n");
				return 1;
			}
			if (0 == iResult) {
				close(sock);
				printf("invalid data received.\n");
				return 1;
			}
			// for debug
			// printf("received:%s.\n", buf);
		}
		else {
			countActive = 0;
		}
    	sum = sum + countActive;
    	
    	mtcsid_temp = strtok(NULL, delim);
    	if (mtcsid_temp == NULL) break;

		if (mode) {
			strcpy(mtcsid, mode);
			strcat(mtcsid, ":");
			strcat(mtcsid, mtcsid_temp);
			strcat(mtcsid, "\n");
		}
		else {
			strcpy(mtcsid, mtcsid_temp);
			strcat(mtcsid, "\n");
		}
	} while (1);
	// for debug
    // printf("sum = %d\n", sum);
	// for production
    printf("%d", sum);

    // close the socket
    close(sock);

    return 0;
}

