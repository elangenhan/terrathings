import * as dev from "./hostbindings";

const led1red = 1;
const led1green = 2;
const led1blue = 3;

function setup(): void {
  dev.delay(1000);

  dev.pinMode(led1red, dev.OUTPUT);
  dev.digitalWrite(led1red, dev.LOW);
  dev.pinMode(led1green, dev.OUTPUT);
  dev.digitalWrite(led1green, dev.LOW);
  dev.pinMode(led1blue, dev.OUTPUT);
  dev.digitalWrite(led1blue, dev.LOW);

  dev.println('🚀 Setup complete');
}

function run(): void {

}

/*
 * Entry point
 */
export function _start(): void {
  setup();
  while (1) {
    run();
  }
}
