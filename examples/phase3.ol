fn factorial(n: int): int {
    if (n <= 1) {
        return 1;
    } else {
        return n * factorial(n - 1);
    }
}

let count: int = 0;
while (count < 5) {
    count = count + 1;
}
let answer: int = factorial(count) + 0;
print(answer);
